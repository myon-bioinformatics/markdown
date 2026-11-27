"""Info-string regressions for the public code_block builder (stdlib only)."""

import itertools
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import markdown as md


class CodeBlockInfoTests(unittest.TestCase):
    def test_info_cannot_extend_only_the_opening_fence(self):
        for marker in ("`", "~"):
            with self.subTest(marker=marker):
                with self.assertRaisesRegex(ValueError, "lang"):
                    md.code_block("body", marker + "tag", fence_char=marker)

    def test_info_rejects_every_separator_used_by_the_reader(self):
        separators = ("\n", "\r", "\r\n", "\v", "\f", "\x1c", "\x1d", "\x1e", "\x85", "\u2028", "\u2029")
        for separator, marker in itertools.product(separators, ("`", "~")):
            for info in (separator + "text", "text" + separator, "text" + separator + "extra"):
                with self.subTest(separator=repr(separator), marker=marker, info=info):
                    with self.assertRaisesRegex(ValueError, "single line"):
                        md.code_block("body", info, fence_char=marker)

    def test_backtick_info_cannot_contain_backticks_anywhere(self):
        # CommonMark 0.31.2 section 4.5 / example 145.
        for info in ("`python", "python`", "python title=`sample.py`", " `python", "\tpython` "):
            with self.subTest(info=info):
                with self.assertRaisesRegex(ValueError, "backtick"):
                    md.code_block("body", info)

    def test_tilde_info_keeps_backticks_tildes_and_separated_leading_tildes(self):
        # CommonMark example 146 allows both kinds of marker in tilde info.
        infos = ("`python", "python title=`sample.py`", "python ~literal~",
                 " ~tag", "\t~~~ details", "  aa ``` ~~~  ")
        for info in infos:
            with self.subTest(info=info):
                generated = md.code_block("body\n", info, fence_char="~")
                self.assertEqual(generated, "~~~" + info + "\nbody\n\n~~~\n")
                block, = md.extract_code_blocks(generated + "# Outside\n")
                self.assertEqual(block, {"language": info.split()[0], "info": info.strip(), "code": "body\n"})
                self.assertEqual(md.extract_sections(generated + "# Outside\n"),
                                 [{"level": 1, "title": "Outside"}])

    def test_valid_info_keeps_existing_output_and_body(self):
        infos = ("", " \t ", "python title=sample.py", "日本語 タイトル=例.txt",
                 'text title="two words"', "{.python #example}", "c++", "text/x-python", "~tag")
        body = "```sample\ntext\n```"
        for info, marker in itertools.product(infos, ("`", "~")):
            if marker == "~" and info == "~tag":
                continue  # Explicitly rejected by the first regression test.
            with self.subTest(info=info, marker=marker):
                delimiter = "````" if marker == "`" else "~~~"
                generated = md.code_block(body, info, fence_char=marker)
                self.assertEqual(generated, f"{delimiter}{info}\n{body}\n{delimiter}\n")
                block, = md.extract_code_blocks(generated)
                self.assertEqual(block["code"], body)
                self.assertEqual(block["info"], info.strip())


if __name__ == "__main__":
    unittest.main()
