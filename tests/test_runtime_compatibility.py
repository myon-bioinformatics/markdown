# Stdlib unittest, not pytest: this lane runs with `python -S` (no
# site-packages) on Python 3.9-3.14 to prove markdown.py works on a bare
# interpreter with nothing installed. pytest is an external module, so it
# cannot run here. All other tests run via `uv run pytest`.
"""Behavior checks runnable using python -S on the source runtime floor."""
import tempfile
import unittest
from pathlib import Path
import markdown

class RuntimeCompatibilityTests(unittest.TestCase):
    def test_headings_ignore_fenced_code(self):
        self.assertEqual(markdown.extract_sections("# Title\n```\n## hidden\n```\n## Next"),
                         [{"level": 1, "title": "Title"}, {"level": 2, "title": "Next"}])

    def test_unicode_file_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / "sample.md")
            markdown.save_markdown("# 日本語\nbody\n", path)
            self.assertEqual(Path(path).read_text(encoding="utf-8"), "# 日本語\nbody\n")
            self.assertIsInstance(markdown.read_markdown(path), dict)

    def test_links_and_code(self):
        self.assertEqual(len(markdown.extract_links("[site](https://example.com)")), 1)
        self.assertEqual(len(markdown.extract_code_blocks("```python\nprint(1)\n```")), 1)
