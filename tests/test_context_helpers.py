from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import markdown as md


SAMPLE = (
    "# Intro\n"
    "ordinary prose\n"
    "## Target\n"
    "target body\n"
    "### Child\n"
    "child body\n"
    "## Next\n"
    "next body\n"
)


def test_extract_section_respects_heading_boundaries() -> None:
    assert md.extract_section(SAMPLE, "Target") == (
        "## Target\n"
        "target body\n"
        "### Child\n"
        "child body\n"
        "## Next\n"
        "next body\n"
    )
    assert md.extract_section(SAMPLE, "intro", level=1) == (
        "# Intro\n"
        "ordinary prose\n"
        "## Target\n"
        "target body\n"
        "### Child\n"
        "child body\n"
    )
    assert md.extract_section(SAMPLE, "tar", partial=True) == (
        "## Target\n"
        "target body\n"
        "### Child\n"
        "child body\n"
    )
    assert md.extract_section(SAMPLE, "missing") == ""


def test_strip_prose_keep_structure_preserves_fences() -> None:
    content = (
        "ordinary prose\n"
        "# Heading\n"
        "another paragraph\n"
        "- item\n"
        "> quote\n"
        "```python\n"
        "ordinary prose inside code\n"
        "```\n"
        "trailer prose\n"
    )
    assert md.strip_prose_keep_structure(content) == (
        "# Heading\n"
        "- item\n"
        "> quote\n"
        "```python\n"
        "ordinary prose inside code\n"
        "```\n"
    )


def test_minify_markdown_is_physical_only() -> None:
    content = "  # Title  \n\n\n<!-- generated -->\n\nbody\n"
    assert md.minify_markdown(content) == "# Title  \n\nbody"
    assert md.minify_markdown(content, strip_html=False) == (
        "# Title  \n\n<!-- generated -->\n\nbody"
    )


def test_safe_truncate_closes_fence_within_limit() -> None:
    content = "before\n```python\nalpha\nbeta\n```\nafter\n"
    result = md.safe_truncate(content, 24)
    assert len(result) <= 24
    assert result.endswith("```")
    blocks = md.extract_code_blocks(result)
    assert len(blocks) == 1
    assert blocks[0]["language"] == "python"


def test_safe_truncate_short_and_invalid_limits() -> None:
    content = "short\n"
    assert md.safe_truncate(content, len(content)) == content
    with pytest.raises(ValueError):
        md.safe_truncate(content, -1)


def test_context_helpers_are_public() -> None:
    for name in (
        "extract_section",
        "strip_prose_keep_structure",
        "minify_markdown",
        "safe_truncate",
    ):
        assert name in md.__all__
        assert hasattr(md, name)
