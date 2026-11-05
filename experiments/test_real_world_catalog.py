"""Synthetic edge cases; not measured report results."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from urllib.parse import unquote, urljoin
from real_world_catalog import catalog_spec, render

RENDERER = Path(os.environ.get('CATALOG_WEB_UI', 'missing-experimental-renderer.py'))

class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.case = self.root / '日本語 & 🧪'
        self.case.mkdir()
        (self.root / 'index.html').write_text('<table><tr><td>keep</td></tr></table><a href="日本語 &amp; 🧪/original.html">original</a>', encoding='utf-8')
        (self.root / 'build_meta.json').write_text(json.dumps({'sha': None, 'dirty': None}))
        self.stats = {'id': self.case.name, 'source': '<script>alert(1)</script>', 'before': dict(h1=1,h2=2,a=3,img=4), 'after': dict(h1=1,h2=0,a=3,img=0)}
        self.save_stats()
        for name in ('original.html', 'roundtrip.html', 'converted.md'):
            (self.case / name).write_text('evidence')

    def save_stats(self):
        (self.case / 'stats.json').write_text(json.dumps(self.stats), encoding='utf-8')

    def test_relative_links_actual_counts_unknown_revision(self):
        spec = catalog_spec(self.root)
        self.assertIn('"sha": null', spec['description'])
        self.assertIn('h2: 2 → 0', spec['items'][0]['summary'])
        for link in spec['items'][0]['links']:
            self.assertTrue((self.root / unquote(link['href'][2:])).is_file())
            self.assertTrue(urljoin('https://example.test/project/nested/catalog-experiment.html', link['href']).startswith('https://example.test/project/nested/'))

    def test_missing_required_or_advertised_image_fails(self):
        (self.case / 'stats.json').unlink()
        with self.assertRaises(ValueError): catalog_spec(self.root)
        self.save_stats()
        (self.root / 'index.html').write_text('<a href="日本語 &amp; 🧪/original.html">original</a><img src="日本語 &amp; 🧪/original.png">', encoding='utf-8')
        with self.assertRaises(ValueError): catalog_spec(self.root)
        (self.case / 'original.png').write_bytes(b'present')
        self.assertTrue(any(x['label'] == 'original.png' for x in catalog_spec(self.root)['items'][0]['links']))

    def test_unadvertised_stale_image_omitted(self):
        (self.case / 'original.png').write_bytes(b'stale')
        self.assertFalse(any(x['label'].endswith('.png') for x in catalog_spec(self.root)['items'][0]['links']))

    @unittest.skipUnless(RENDERER.is_file(), 'set CATALOG_WEB_UI to pinned renderer')
    def test_escape_determinism_no_mutation(self):
        def hashes(): return {p.relative_to(self.root): hashlib.sha256(p.read_bytes()).hexdigest() for p in self.root.rglob('*') if p.is_file()}
        before = hashes()
        page = render(self.root, RENDERER)
        self.assertEqual(page, render(self.root, RENDERER))
        self.assertIn('&lt;script&gt;', page)
        self.assertNotIn('<script>', page)
        self.assertIn('name="viewport"', page)
        self.assertEqual(before, hashes())

    def test_escaping_symlink_bad_counts(self):
        (self.case / 'converted.md').unlink()
        (self.case / 'converted.md').symlink_to('/etc/hosts')
        with self.assertRaises(ValueError): catalog_spec(self.root)
        (self.case / 'converted.md').unlink()
        (self.case / 'converted.md').write_text('ok')
        self.stats['before']['a'] = True
        self.save_stats()
        with self.assertRaises(ValueError): catalog_spec(self.root)

    def test_stale_fixture_not_in_current_index_is_omitted(self):
        extra = self.root / 'old'
        extra.mkdir()
        (extra / 'stats.json').write_text('{}')
        self.assertEqual(len(catalog_spec(self.root)['items']), 1)

    def test_wrong_renderer_not_executed(self):
        wrong = self.root / 'wrong.py'
        wrong.write_text('raise RuntimeError("must not execute")')
        with self.assertRaises(ValueError): render(self.root, wrong)


class BrowserVerifierTests(unittest.TestCase):
    """Synthetic browser responses, including every rejection under -O/-OO."""

    def test_acceptance_checks_at_every_optimization_level(self):
        from unittest.mock import MagicMock
        source = Path(__file__).with_name('check_catalog_browser.py').read_text()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'evidence.json').write_text('{}')
            for optimization in (0, 1, 2):
                namespace = {'__name__': 'browser_verifier_test'}
                exec(compile(source, 'check_catalog_browser.py', 'exec',
                             optimize=optimization), namespace)
                for failure in (None, 'article', 'script', 'overflow', 'open',
                                'close', 'missing', 'navigation', 'stats'):
                    with self.subTest(optimization=optimization, failure=failure):
                        page = MagicMock()
                        locators = {key: MagicMock() for key in
                                    ('article', 'script', 'summary', 'details[open]',
                                     'article a', 'body')}
                        page.locator.side_effect = locators.__getitem__
                        locators['article'].count.return_value = 0 if failure == 'article' else 1
                        locators['script'].count.return_value = 1 if failure == 'script' else 0
                        page.evaluate.return_value = 321 if failure == 'overflow' else 320
                        locators['details[open]'].count.side_effect = (
                            [0, 0] if failure == 'open' else
                            [1, 1] if failure == 'close' else [1, 0])
                        locators['article a'].evaluate_all.return_value = [
                            './missing.json' if failure == 'missing' else './evidence.json']
                        page.url = ('file:///wrong.html' if failure == 'navigation'
                                    else 'file:///tohoho_web_home/roundtrip.html')
                        locators['body'].inner_text.return_value = (
                            '{}' if failure == 'stats' else '{"h2": 24}')
                        if failure is None:
                            namespace['check_page'](page, root, 320)
                            self.assertEqual(page.keyboard.press.call_count, 2)
                            page.go_back.assert_called_once()
                        else:
                            with self.assertRaisesRegex(RuntimeError, 'Browser check failed:'):
                                namespace['check_page'](page, root, 320)

if __name__ == '__main__': unittest.main()
