"""Regression tests for the follow-up issues in #63."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import markdown as md


def test_markdown_to_man_replaces_nul_in_body_and_rejects_header_controls() -> None:
    fence = "\x60\x60\x60"
    content = "paragraph before\x00after\n\n" + fence + "\ncode before\x00after\n" + fence
    out = md.markdown_to_man(content, name="demo")
    assert "\x00" not in out
    assert "paragraph before\uFFFDafter" in out
    assert "code before\uFFFDafter" in out
    with pytest.raises(ValueError, match="control characters"):
        md.markdown_to_man("", name="demo\x00name")


def test_compact_llm_output_preserves_info_string_and_is_idempotent() -> None:
    fence = "\x60\x60\x60"
    text = fence + "python title=example.py\nline1\nline2\nline3\nline4\n" + fence + "\n"
    compacted = md.compact_llm_output(text, max_code_lines=2)
    assert compacted.startswith(fence + "python title=example.py\n")
    assert "… 2 more lines" in compacted
    assert md.compact_llm_output(compacted, max_code_lines=2) == compacted


def test_split_reasoning_balances_nested_details() -> None:
    text = (
        "before\n"
        '<details type="reasoning">\n'
        "<summary>outer summary</summary>\n"
        "outer start\n"
        "<details><summary>inner summary</summary>inner body</details>\n"
        "outer end\n"
        "</details>\n"
        "after\n"
    )
    result = md.split_reasoning(text)
    assert result["formats"] == ["details"]
    assert "inner summary" in result["reasoning"][0]
    assert "inner body</details>" in result["reasoning"][0]
    assert result["reasoning"][0].endswith("outer end")
    assert result["answer"] == "before\n\nafter\n"


def test_markdown_to_chat_messages_preserves_non_lf_separators() -> None:
    text = (
        "## User\r\n"
        "first\rsecond\vthird\ffourth\u2028fifth\u2029sixth\n"
        "## Assistant\n"
        "ok\n"
    )
    messages = md.markdown_to_chat_messages(text)
    assert messages == [
        {"role": "user", "content": "first\rsecond\vthird\ffourth\u2028fifth\u2029sixth"},
        {"role": "assistant", "content": "ok"},
    ]


def test_directory_to_markdown_rejects_zero_max_depth(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="max_depth must be >= 1"):
        md.directory_to_markdown(tmp_path, max_depth=0)


def test_scanner_preserves_legacy_fence_close_with_trailing_text() -> None:
    fence = "\x60\x60\x60"
    scanned = md._scan_lines([fence, "inside", fence + "inner", "outside"])
    assert scanned[2].is_fence_close
    assert not scanned[3].in_fenced_code


def test_tree_text_treats_literal_arrow_name_as_ambiguous_symlink() -> None:
    assert md.tree_text_to_markdown("root\n└── report -> backup\n") == "- report\n"


def test_compact_llm_output_zero_limit_and_tilde_fence_are_idempotent() -> None:
    fence = "~~~"
    text = fence + "python title=example.py\nline1\nline2\n" + fence + "\n"
    compacted = md.compact_llm_output(text, max_code_lines=0)
    assert compacted.startswith(fence + "python title=example.py\\n")
    assert "… 2 more lines" in compacted
    assert md.compact_llm_output(compacted, max_code_lines=0) == compacted


def test_split_reasoning_preserves_nested_summary_when_outer_has_none() -> None:
    text = (
        '<details type="reasoning">\n'
        "outer start\n"
        "<details><summary>inner summary</summary>inner body</details>\n"
        "outer end\n"
        "</details>\n"
        "answer\n"
    )
    result = md.split_reasoning(text)
    assert result["reasoning"] == [
        "outer start\\n<details><summary>inner summary</summary>inner body</details>\\nouter end"
    ]
    assert result["answer"] == "answer\\n"


def test_split_reasoning_unclosed_nested_details_consumes_remainder() -> None:
    text = '<details type="reasoning">outer<details>inner</details>tail'
    result = md.split_reasoning(text)
    assert result["reasoning"] == ["outer<details>inner</details>tail"]
    assert result["answer"] == ""
