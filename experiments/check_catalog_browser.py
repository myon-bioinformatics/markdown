"""Explicit local browser check; never dispatched by Pages or default CI."""
import argparse
import functools
import http.server
from pathlib import Path
import threading
from urllib.parse import unquote, urlsplit
from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--report', required=True, type=Path)
    parser.add_argument('--chromium', required=True)
    parser.add_argument('--screenshots', required=True, type=Path)
    args = parser.parse_args()
    args.screenshots.mkdir(parents=True, exist_ok=True)
    root = args.report.resolve()
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(http.server.SimpleHTTPRequestHandler, directory=root.parent))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    origin = f'http://127.0.0.1:{server.server_port}'
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(executable_path=args.chromium, args=['--no-sandbox'])
            try:
                for width in (320, 390, 1440):
                    for transport in ('http', 'file'):
                        context = browser.new_context(java_script_enabled=False, viewport={'width': width, 'height': 844})
                        try:
                            page = context.new_page()
                            base = origin + '/' + root.name + '/' if transport == 'http' else root.as_uri() + '/'
                            page.goto(base + 'catalog-experiment.html')
                            assert page.locator('article').count() == 1
                            assert page.locator('script').count() == 0
                            assert page.evaluate('document.documentElement.scrollWidth') <= width
                            summary = page.locator('summary').first
                            summary.focus()
                            page.keyboard.press('Enter')
                            assert page.locator('details[open]').count() == 1
                            page.keyboard.press('Enter')
                            assert page.locator('details[open]').count() == 0
                            page.screenshot(path=str(args.screenshots / f'{transport}-{width}.png'), full_page=True)
                            hrefs = page.locator('article a').evaluate_all('(links) => links.map(a => a.getAttribute("href"))')
                            for href in hrefs:
                                assert (root / unquote(urlsplit(href).path)).is_file(), href
                            page.get_by_role('link', name='roundtrip.html', exact=True).click()
                            assert page.url.endswith('/tohoho_web_home/roundtrip.html')
                            page.go_back()
                            page.get_by_role('link', name='stats.json', exact=True).click()
                            assert '"h2": 24' in page.locator('body').inner_text()
                            print(f'PASS {transport} width={width}: layout, keyboard details, relative evidence links')
                        finally:
                            context.close()
            finally:
                browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

if __name__ == '__main__': main()
