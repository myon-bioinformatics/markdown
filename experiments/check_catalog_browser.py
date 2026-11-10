"""Explicit local browser check; never dispatched by Pages or default CI."""
import argparse, functools, http.server, threading
from pathlib import Path; from urllib.parse import unquote, urlsplit


def check_page(page, root, width):
    """Fail explicitly even when Python assertion statements are optimized out."""
    if not page.locator('article').count() == 1:
        raise RuntimeError("Browser check failed: page.locator('article').count() == 1")
    if not page.locator('script').count() == 0:
        raise RuntimeError("Browser check failed: page.locator('script').count() == 0")
    if not page.evaluate('document.documentElement.scrollWidth') <= width:
        raise RuntimeError("Browser check failed: page.evaluate('document.documentElement.scrollWidth') <= width")
    summary = page.locator('summary').first
    summary.focus()
    page.keyboard.press('Enter')
    if not page.locator('details[open]').count() == 1:
        raise RuntimeError("Browser check failed: page.locator('details[open]').count() == 1")
    page.keyboard.press('Enter')
    if not page.locator('details[open]').count() == 0:
        raise RuntimeError("Browser check failed: page.locator('details[open]').count() == 0")
    hrefs = page.locator('article a').evaluate_all('(links) => links.map(a => a.getAttribute("href"))')
    for href in hrefs:
        if not (root / unquote(urlsplit(href).path)).is_file():
            raise RuntimeError(f'Browser check failed: missing evidence link {href!r}')
    page.get_by_role('link', name='roundtrip.html', exact=True).click()
    if not page.url.endswith('/tohoho_web_home/roundtrip.html'):
        raise RuntimeError("Browser check failed: page.url.endswith('/tohoho_web_home/roundtrip.html')")
    page.go_back()
    page.get_by_role('link', name='stats.json', exact=True).click()
    if not '"h2": 24' in page.locator('body').inner_text():
        raise RuntimeError('Browser check failed: \'"h2": 24\' in page.locator(\'body\').inner_text()')


def main(argv=None):
    from playwright.sync_api import sync_playwright

    parser = argparse.ArgumentParser()
    parser.add_argument('--report', required=True, type=Path)
    parser.add_argument('--chromium', required=True)
    parser.add_argument('--screenshots', required=True, type=Path)
    args = parser.parse_args(argv)
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
                            check_page(page, root, width)
                            page.goto(base + 'catalog-experiment.html')
                            page.screenshot(path=str(args.screenshots / f'{transport}-{width}.png'), full_page=True)
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
