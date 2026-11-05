"""Opt-in, offline catalog of an already generated real-world Pages report.

No adoption/vendor pin or deployment change. Pass the exact web-ui #111 file.
"""
from __future__ import annotations

import argparse
import hashlib
from html.parser import HTMLParser
import importlib.util
import json
import os
import tempfile
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit

WEB_UI_COMMIT = '96079aba4084e11834c4d9c70d40eea3f5b326bd'
WEB_UI_SHA256 = '75531bd58c523a6e5ecc92580f78d012e6747e927dcfd4887c9314b10c8e8a0b'
REQUIRED = ('stats.json', 'converted.md', 'roundtrip.html', 'original.html')
IMAGES = ('original.png', 'roundtrip.png')


class ReportImages(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.paths = set()
        self.fixtures = set()
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            href = dict(attrs).get('href', '')
            url = urlsplit(href)
            parts = unquote(url.path).removeprefix('./').split('/')
            if not url.scheme and not url.netloc and not url.query and not url.fragment and len(parts) == 2 and parts[1] == 'original.html':
                if parts[0] in ('', '.', '..'):
                    raise ValueError('Invalid fixture path in report')
                self.fixtures.add(parts[0])
        if tag == 'img':
            src = dict(attrs).get('src', '')
            url = urlsplit(src)
            if not url.scheme and not url.netloc and not url.query and not url.fragment:
                self.paths.add(unquote(url.path).removeprefix('./'))


def evidence(root: Path, relative: str) -> Path:
    path = root / relative
    if not path.resolve().is_relative_to(root) or not path.is_file():
        raise ValueError(f'Missing or escaping evidence: {relative}')
    return path


def catalog_spec(report: Path) -> dict:
    root = report.resolve(strict=True)
    index = evidence(root, 'index.html').read_text(encoding='utf-8')
    meta = json.loads(evidence(root, 'build_meta.json').read_text(encoding='utf-8'))
    if not isinstance(meta, dict):
        raise ValueError('build_meta.json must be an object')
    parsed = ReportImages(index)
    images = parsed.paths
    items = []
    for name in sorted(parsed.fixtures):
        paths = {n: evidence(root, f'{name}/{n}') for n in REQUIRED}
        stats = json.loads(paths['stats.json'].read_text(encoding='utf-8'))
        if not isinstance(stats, dict):
            raise ValueError(f'Invalid stats object: {name}')
        if stats.get('id') != name or not isinstance(stats.get('source'), str):
            raise ValueError(f'Invalid fixture identity/source: {name}')
        for key in ('before', 'after'):
            counts = stats.get(key)
            if not isinstance(counts, dict) or set(counts) != {'h1', 'h2', 'a', 'img'}:
                raise ValueError(f'Invalid counts: {name}/{key}')
            if any(type(v) is not int or v < 0 for v in counts.values()):
                raise ValueError(f'Invalid count value: {name}/{key}')
        links = [{'label': n, 'href': './' + quote(f'{name}/{n}', safe='/')} for n in REQUIRED]
        missing_images = []
        for image in IMAGES:
            relative = f'{name}/{image}'
            if relative in images:
                evidence(root, relative)
                links.append({'label': image, 'href': './' + quote(relative, safe='/')})
            else:
                missing_images.append(image)
        links += [{'label': 'Existing report (tables and images)', 'href': './index.html'},
                  {'label': 'Build revision JSON', 'href': './build_meta.json'}]
        summary = '; '.join(f"{tag}: {stats['before'][tag]} → {stats['after'][tag]}" for tag in ('h1', 'h2', 'a', 'img'))
        items.append({'id': 'fixture-' + hashlib.sha256(name.encode()).hexdigest(),
                      'title': name, 'category': 'Vendored HTML fixture', 'summary': summary,
                      'details': 'Source: ' + stats['source'] + '\nImages unavailable in report: ' + (', '.join(missing_images) or 'none'),
                      'links': links})
    if not items:
        raise ValueError('No generated fixture evidence found')
    return {'schema': 'web-ui-catalog/1', 'title': 'Real-world HTML fixture catalog (experiment)',
            'description': 'Existing generated report; offline vendored snapshots, not live site measurements.\nBuild metadata: ' + json.dumps(meta, ensure_ascii=False, sort_keys=True),
            'items': items}


def render(report: Path, renderer: Path) -> str:
    raw = renderer.read_bytes()
    if hashlib.sha256(raw).hexdigest() != WEB_UI_SHA256:
        raise ValueError('Expected the exact web-ui #111 pinned renderer')
    spec = catalog_spec(report)
    module_spec = importlib.util.spec_from_file_location('experimental_catalog_web_ui', renderer)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module.catalog_document(spec)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', required=True, type=Path)
    parser.add_argument('--web-ui', required=True, type=Path)
    args = parser.parse_args()
    page = render(args.report, args.web_ui)
    output = args.report / 'catalog-experiment.html'
    if output.is_symlink():
        raise ValueError('Refusing symlink output')
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', newline='\n', dir=args.report, delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(page)
        os.replace(temporary, output)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
