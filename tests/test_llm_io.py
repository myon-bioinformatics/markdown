from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import markdown as md


def test_exports() -> None:
    for name in (
        "split_reasoning",
        "compact_llm_output",
        "llm_output_digest",
        "extract_identifiers",
    ):
        assert name in md.__all__


# --- split_reasoning ---------------------------------------------------------


@pytest.mark.parametrize("tag", ["think", "thinking", "reasoning"])
def test_split_reasoning_recognizes_each_tag_format(tag: str) -> None:
    result = md.split_reasoning(f"<{tag}>pondering</{tag}>The answer.\n")
    assert result == {
        "answer": "The answer.\n",
        "reasoning": ["pondering"],
        "formats": [tag],
    }


def test_split_reasoning_is_case_insensitive_and_tolerates_attributes() -> None:
    result = md.split_reasoning('<THINK class="x">hello</THINK>ans')
    assert result == {"answer": "ans\n", "reasoning": ["hello"], "formats": ["think"]}


def test_split_reasoning_openwebui_details_drops_summary_line() -> None:
    text = (
        '<details type="reasoning" done="true" duration="12">\n'
        "<summary>Thought for 12 seconds</summary>\n"
        "Let me work through this step by step.\n"
        "The answer is 42.\n"
        "</details>\n"
        "\n"
        "The answer is 42.\n"
    )
    result = md.split_reasoning(text)
    assert result["formats"] == ["details"]
    assert result["reasoning"] == ["Let me work through this step by step.\nThe answer is 42."]
    assert "Thought for 12 seconds" not in result["reasoning"][0]
    assert result["answer"] == "The answer is 42.\n"


def test_split_reasoning_ignores_tags_in_fenced_code() -> None:
    text = "Use `<think>` in prompts.\n\n```\n<think>fake</think>\n```\n\nReal answer.\n"
    result = md.split_reasoning(text)
    assert result == {"answer": text, "reasoning": [], "formats": []}


def test_split_reasoning_ignores_tags_in_inline_code() -> None:
    text = "before `<reasoning>x</reasoning>` after\n"
    result = md.split_reasoning(text)
    assert result == {"answer": text, "reasoning": [], "formats": []}


def test_split_reasoning_plain_details_without_reasoning_type_is_not_reasoning() -> None:
    text = "<details><summary>Click me</summary>body</details>ans"
    result = md.split_reasoning(text)
    assert result == {"answer": text + "\n", "reasoning": [], "formats": []}


def test_split_reasoning_unclosed_tag_makes_the_rest_reasoning() -> None:
    result = md.split_reasoning("Before.\n<think>\nI was thinking and then the stream")
    assert result == {
        "answer": "Before.\n",
        "reasoning": ["I was thinking and then the stream"],
        "formats": ["think"],
    }


def test_split_reasoning_unclosed_openwebui_details() -> None:
    text = '<details type="reasoning">\n<summary>Thinking</summary>\ncut off mid'
    result = md.split_reasoning(text)
    assert result["formats"] == ["details"]
    assert result["answer"] == ""
    assert "cut off mid" in result["reasoning"][0]


def test_split_reasoning_multiple_blocks_in_order() -> None:
    result = md.split_reasoning("<think>one</think>Body<reasoning>two</reasoning> end")
    assert result["reasoning"] == ["one", "two"]
    assert result["formats"] == ["think", "reasoning"]
    assert result["answer"] == "Body end\n"


def test_split_reasoning_collapses_blank_runs_left_behind() -> None:
    result = md.split_reasoning("Before\n<think>\nreasoning\n</think>\n\nAfter\n")
    assert result["answer"] == "Before\n\nAfter\n"


def test_split_reasoning_pure_reasoning_leaves_empty_answer() -> None:
    result = md.split_reasoning("<think>only reasoning, no answer</think>")
    assert result["answer"] == ""
    assert result["reasoning"] == ["only reasoning, no answer"]


def test_split_reasoning_empty_input() -> None:
    assert md.split_reasoning("") == {"answer": "", "reasoning": [], "formats": []}


def test_split_reasoning_rejects_non_string() -> None:
    with pytest.raises(ValueError):
        md.split_reasoning(123)  # type: ignore[arg-type]


# --- compact_llm_output -------------------------------------------------------


def test_compact_llm_output_drops_reasoning_by_default() -> None:
    text = "<think>long private reasoning</think>Line1\n\n\n\nLine2\n"
    assert md.compact_llm_output(text) == "Line1\n\nLine2\n"


def test_compact_llm_output_keep_reasoning_true_keeps_tags() -> None:
    text = "<think>long private reasoning</think>Line1\n\n\n\nLine2\n"
    out = md.compact_llm_output(text, keep_reasoning=True)
    assert "<think>long private reasoning</think>" in out
    assert out == "<think>long private reasoning</think>Line1\n\nLine2\n"


def test_compact_llm_output_max_blank_lines_is_configurable() -> None:
    text = "Line1\n\n\n\nLine2\n"
    assert md.compact_llm_output(text, max_blank_lines=0) == "Line1\nLine2\n"
    assert md.compact_llm_output(text, max_blank_lines=2) == "Line1\n\n\nLine2\n"


def test_compact_llm_output_short_code_block_is_untouched() -> None:
    code = "\n".join(f"line{i}" for i in range(1, 41))
    text = f"```python\n{code}\n```\n"
    assert md.compact_llm_output(text, max_code_lines=40) == text


def test_compact_llm_output_truncates_long_code_block_with_marker() -> None:
    code = "\n".join(f"line{i}" for i in range(1, 51))
    text = f"```python\n{code}\n```\n"
    out = md.compact_llm_output(text, max_code_lines=5)
    lines = out.splitlines()
    assert lines[:7] == ["```python", "line1", "line2", "line3", "line4", "line5", "… 45 more lines"]
    assert lines[-1] == "```"
    # Never alter kept code content.
    for i in range(1, 6):
        assert f"line{i}" in out
    assert "line50" not in out


def test_compact_llm_output_truncation_keeps_fence_stable_with_backtick_runs() -> None:
    # The outer fence must already be 4 backticks for an inner ``` line to be
    # legitimate content; this is exactly what the adaptive fence protects.
    inner = ["line1", "```", "line3"] + [f"line{i}" for i in range(4, 51)]
    text = "````python\n" + "\n".join(inner) + "\n````\n"
    out = md.compact_llm_output(text, max_code_lines=5)
    blocks = md.extract_code_blocks(out)
    assert len(blocks) == 1
    assert blocks[0]["language"] == "python"
    assert blocks[0]["code"].splitlines()[:6] == ["line1", "```", "line3", "line4", "line5", "… 45 more lines"]
    # The re-fence must be longer than the ``` run now inside the body.
    assert out.count("````") == 2


def test_compact_llm_output_truncation_preserves_tilde_fence() -> None:
    # A ~~~-fenced block must stay ~~~-fenced after truncation, not switch to
    # backtick (code_block()'s default), and its own adaptive fence still
    # grows past a ~~~ run left inside the kept body.
    text = "~~~python\n" + "\n".join(f"line{i}" for i in range(1, 51)) + "\n~~~\n"
    out = md.compact_llm_output(text, max_code_lines=5)
    assert out.startswith("~~~python\n")
    assert "```" not in out

    inner = ["a", "~~~", "b"] + [f"line{i}" for i in range(4, 51)]
    text_with_run = "~~~~python\n" + "\n".join(inner) + "\n~~~~\n"
    out_with_run = md.compact_llm_output(text_with_run, max_code_lines=5)
    assert out_with_run.count("~~~~") == 2


def test_compact_llm_output_empty_input() -> None:
    assert md.compact_llm_output("") == ""


@pytest.mark.parametrize(
    "kwargs",
    [{"max_code_lines": -1}, {"max_blank_lines": -1}],
)
def test_compact_llm_output_rejects_negative_params(kwargs: dict) -> None:
    with pytest.raises(ValueError):
        md.compact_llm_output("hello", **kwargs)


def test_compact_llm_output_rejects_non_string() -> None:
    with pytest.raises(ValueError):
        md.compact_llm_output(None)  # type: ignore[arg-type]


# --- llm_output_digest ---------------------------------------------------------


def test_llm_output_digest_fields() -> None:
    text = (
        "<think>secret</think>"
        "# Title\n\n"
        "Some answer [link](https://example.com).\n\n"
        "```python\nprint(1)\n```\n"
    )
    digest = md.llm_output_digest(text)
    assert digest["reasoning_blocks"] == 1
    assert digest["reasoning_chars"] == len("secret")
    assert digest["headings"] == ["Title"]
    assert digest["code_blocks"] == [{"lang": "python", "lines": 1}]
    assert digest["links"] == ["https://example.com"]
    assert digest["has_table"] is False
    assert digest["answer_chars"] == len(md.split_reasoning(text)["answer"])


def test_llm_output_digest_has_table() -> None:
    with_table = "| a | b |\n| --- | --- |\n| 1 | 2 |\n"
    assert md.llm_output_digest(with_table)["has_table"] is True
    assert md.llm_output_digest("no table here\n")["has_table"] is False


def test_llm_output_digest_multiple_reasoning_blocks() -> None:
    digest = md.llm_output_digest("<think>one</think>Body<reasoning>two</reasoning> end")
    assert digest["reasoning_blocks"] == 2
    assert digest["reasoning_chars"] == len("one") + len("two")


def test_llm_output_digest_empty_input() -> None:
    assert md.llm_output_digest("") == {
        "answer_chars": 0,
        "reasoning_chars": 0,
        "reasoning_blocks": 0,
        "headings": [],
        "code_blocks": [],
        "links": [],
        "has_table": False,
    }


def test_llm_output_digest_rejects_non_string() -> None:
    with pytest.raises(ValueError):
        md.llm_output_digest(123)  # type: ignore[arg-type]


# --- extract_identifiers -------------------------------------------------------


def test_extract_identifiers_finds_each_category() -> None:
    text = (
        "See 550e8400-e29b-41d4-a716-446655440000 and "
        "https://example.com/path plus deadbeef123 alone. "
        "Also myon-bioinformatics/markdown#61 and bare #7.\n"
    )
    ids = md.extract_identifiers(text)
    assert ids["uuids"] == ["550e8400-e29b-41d4-a716-446655440000"]
    assert ids["urls"] == ["https://example.com/path"]
    assert ids["github_refs"] == ["myon-bioinformatics/markdown#61", "#7"]
    assert ids["shas"] == ["deadbeef123"]


def test_extract_identifiers_uuid_is_not_split_into_shas() -> None:
    ids = md.extract_identifiers("id 550e8400-e29b-41d4-a716-446655440000 here\n")
    assert ids["shas"] == []
    assert ids["uuids"] == ["550e8400-e29b-41d4-a716-446655440000"]


def test_extract_identifiers_urls_hex_is_not_counted_as_a_sha() -> None:
    ids = md.extract_identifiers("see https://x.com/commit/abcdef1234567 now\n")
    assert ids["shas"] == []
    assert ids["urls"] == ["https://x.com/commit/abcdef1234567"]


def test_extract_identifiers_pure_digit_or_pure_letter_runs_are_not_shas() -> None:
    ids = md.extract_identifiers("call 1234567 and deadbeef please\n")
    assert ids["shas"] == []


def test_extract_identifiers_skips_fenced_code_but_not_inline_code() -> None:
    text = (
        "inline `deadbeef123` stays\n\n"
        "```\n"
        "ffffffff9 550e8400-e29b-41d4-a716-446655440000\n"
        "```\n"
    )
    ids = md.extract_identifiers(text)
    assert ids["shas"] == ["deadbeef123"]
    assert ids["uuids"] == []


def test_extract_identifiers_skips_urls_and_github_refs_in_fenced_code_too() -> None:
    text = (
        "real https://example.com/x and myon/repo#9 here.\n\n"
        "```\n"
        "https://fenced.example.com/y and other/thing#3\n"
        "```\n"
    )
    ids = md.extract_identifiers(text)
    assert ids["urls"] == ["https://example.com/x"]
    assert ids["github_refs"] == ["myon/repo#9"]


def test_extract_identifiers_dedupes_in_order_of_appearance() -> None:
    text = "dup #5 stuff #5 again, then #9, then #5 once more\n"
    ids = md.extract_identifiers(text)
    assert ids["github_refs"] == ["#5", "#9"]


def test_extract_identifiers_empty_input() -> None:
    assert md.extract_identifiers("") == {
        "uuids": [],
        "urls": [],
        "github_refs": [],
        "shas": [],
    }


def test_extract_identifiers_rejects_non_string() -> None:
    with pytest.raises(ValueError):
        md.extract_identifiers(123)  # type: ignore[arg-type]
