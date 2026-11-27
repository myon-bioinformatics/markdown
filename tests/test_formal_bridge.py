"""Connect the line-level Lean reader theorem to the real Markdown helpers.

Exhaustive short bodies exercise state transitions beyond the hand-written
fence examples in test_syntax.py. No pytest, renderer or Lean is required.
"""

import itertools
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import markdown as md


def longest_run(text, marker):
    """Independent streaming count; do not reuse the production regex."""
    longest = current = 0
    for char in text:
        current = current + 1 if char == marker else 0
        longest = max(longest, current)
    return longest


class FenceRoundtripBridge(unittest.TestCase):
    def test_all_short_bodies_preserve_payload_and_scanner_boundaries(self):
        # 5,461 bodies, each with both legal fence characters. The alphabet
        # includes competing markers, a run-breaking character and LF.
        for size in range(7):
            for chars in itertools.product(("`", "~", "x", "\n"), repeat=size):
                body = "".join(chars)
                for marker in ("`", "~"):
                    with self.subTest(body=body, marker=marker):
                        generated = md.code_block(body, "text", fence_char=marker)
                        delimiter = md._adaptive_fence(body, marker)
                        self.assertEqual(len(delimiter), max(3, longest_run(body, marker) + 1))
                        scanned = md._scan_lines(generated.splitlines())
                        self.assertTrue(scanned[0].is_fence_open)
                        self.assertTrue(scanned[-1].is_fence_close)
                        self.assertEqual([row.text for row in scanned[1:-1]], body.split("\n"))
                        self.assertTrue(all(row.in_fenced_code and not row.is_fence_open
                                            and not row.is_fence_close for row in scanned[1:-1]))
                        self.assertEqual(md.extract_code_blocks(generated), [
                            {"language": "text", "info": "text", "code": body},
                        ])

    def test_nested_wrapping_preserves_each_layer_and_leaves_the_suffix_live(self):
        payload = "# 内側\n```sample\nbody\n```\n~~~\n\n"
        originals = []
        for level in range(12):
            originals.append(payload)
            marker = "`" if level % 2 == 0 else "~"
            payload = md.code_block(payload, "markdown", fence_char=marker)
            suffix = "# Outside\n" + md.code_block("tail", "text", fence_char="~")
            blocks = md.extract_code_blocks(payload + suffix)
            self.assertEqual([block["code"] for block in blocks], [originals[-1], "tail"])
            self.assertEqual(md.extract_sections(payload + suffix), [{"level": 1, "title": "Outside"}])
        for original in reversed(originals):
            payload = md.extract_code_blocks(payload)[0]["code"]
            self.assertEqual(payload, original)

    def test_lf_unicode_and_trailing_empty_lines_are_preserved(self):
        bodies = ["日本語🙂\n", "e\u0301\n\n", "\t`````suffix\n\x00\n~~~", "\n\n結末\n\n"]
        infos = ["", "python title=sample.py", "日本語 タイトル=例.txt", "  text title=two  "]
        for body, info, marker in itertools.product(bodies, infos, ("`", "~")):
            with self.subTest(body=body, info=info, marker=marker):
                block, = md.extract_code_blocks(md.code_block(body, info, fence_char=marker))
                self.assertEqual(block["code"], body)
                self.assertEqual(block["info"], info.strip())
                self.assertEqual(block["language"], info.split()[0] if info.split() else "")

    def test_other_line_separators_are_normalized_not_claimed_byte_exact(self):
        # splitlines() is part of extract_code_blocks, outside the Lean model.
        for separator in ("\r", "\r\n", "\v", "\f", "\x1c", "\x1d", "\x1e", "\x85", "\u2028", "\u2029"):
            with self.subTest(separator=repr(separator)):
                body = "left" + separator + "right"
                block, = md.extract_code_blocks(md.code_block(body))
                self.assertEqual(block["code"], "left\nright")
                self.assertNotEqual(block["code"], body)


if __name__ == "__main__":
    unittest.main()
