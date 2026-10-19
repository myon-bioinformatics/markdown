"""Tests for slugify and table_of_contents functions in markdown.py."""

import pytest
import markdown as md


def test_slugify_basic():
    assert md.slugify("Hello World!") == "hello-world"
    assert md.slugify("User & Permissions (v2.0)") == "user--permissions-v20"
    assert md.slugify("  Spaces   And\tTabs  ") == "spaces---andtabs"


def test_slugify_formatting_and_links():
    assert md.slugify("Heading with `code` and **bold**") == "heading-with-code-and-bold"
    assert md.slugify("Click [here](https://example.com) for details") == "click-here-for-details"


def test_slugify_unicode():
    assert md.slugify("日本語の見出し 1.0") == "日本語の見出し-10"


def test_table_of_contents_basic():
    content = """# Title
## Section 1
### Subsection 1.1
## Section 2
"""
    toc = md.table_of_contents(content)
    assert toc == (
        "- [Title](#title)\n"
        "  - [Section 1](#section-1)\n"
        "    - [Subsection 1.1](#subsection-11)\n"
        "  - [Section 2](#section-2)\n"
    )


def test_table_of_contents_level_filtering():
    content = """# H1
## H2
### H3
#### H4
"""
    toc = md.table_of_contents(content, min_level=2, max_level=3)
    assert toc == (
        "- [H2](#h2)\n"
        "  - [H3](#h3)\n"
    )


def test_table_of_contents_duplicate_slugs():
    content = """# Overview
## Overview
### Overview
"""
    toc = md.table_of_contents(content)
    assert toc == (
        "- [Overview](#overview)\n"
        "  - [Overview](#overview-1)\n"
        "    - [Overview](#overview-2)\n"
    )


def test_table_of_contents_fenced_code_ignored():
    content = """# Real Heading

```markdown
# Ignored Code Heading
```

## Another Real Heading
"""
    toc = md.table_of_contents(content)
    assert toc == (
        "- [Real Heading](#real-heading)\n"
        "  - [Another Real Heading](#another-real-heading)\n"
    )


def test_table_of_contents_invalid_level_bounds():
    with pytest.raises(ValueError):
        md.table_of_contents("# Test", min_level=0)
    with pytest.raises(ValueError):
        md.table_of_contents("# Test", max_level=7)
    with pytest.raises(ValueError):
        md.table_of_contents("# Test", min_level=3, max_level=2)


def test_table_of_contents_no_headings():
    assert md.table_of_contents("Just prose without headings.") == ""


@pytest.mark.parametrize("source, kwargs, expected", [
    ("# Repeat\n## Repeat", {"min_level": 2}, "- [Repeat](#repeat-1)\n"),
    ("### Repeat\n## Repeat", {"max_level": 2}, "- [Repeat](#repeat-1)\n"),
    ("# A\n# A\n# A-1", {}, "- [A](#a)\n- [A](#a-1)\n- [A-1](#a-1-1)\n"),
    ("# A-1\n# A\n# A", {}, "- [A-1](#a-1)\n- [A](#a)\n- [A](#a-2)\n"),
    ("# `code`", {}, "- [code](#code)\n"),
    ("# `code` and **bold**", {}, "- [code and bold](#code-and-bold)\n"),
    ("# [API](https://example.com)", {}, "- [API](#api)\n"),
    ("   # Indented ###", {}, "- [Indented](#indented)\n"),
    ("#\n## ###", {}, "- [](#)\n  - [](#-1)\n"),
    ("    # Code\n# Real", {}, "- [Real](#real)\n"),
    ("<!--\n# Hidden\n-->\n# Visible", {}, "- [Visible](#visible)\n"),
    ("<!--\n```\n-->\n# Visible", {}, "- [Visible](#visible)\n"),
    ("~~~\n# Hidden\n~~~\n# Visible", {}, "- [Visible](#visible)\n"),
])
def test_table_of_contents_regressions(source, kwargs, expected):
    assert md.table_of_contents(source, **kwargs) == expected


@pytest.mark.parametrize("heading, expected", [
    ("foo_bar", "foo_bar"),
    ("Hello  World", "hello--world"),
    ("Cafe\u0301", "cafe\u0301"),
    ("Hello\tWorld", "helloworld"),
    ("_Italic_ and **bold**", "italic-and-bold"),
    ("日本語 😀", "日本語-"),
])
def test_slugify_github_style_subset(heading, expected):
    assert md.slugify(heading) == expected


@pytest.mark.parametrize("value", [True, False, 1.5, "2", None])
@pytest.mark.parametrize("argument", ["min_level", "max_level"])
def test_table_of_contents_non_integer_bounds(value, argument):
    with pytest.raises(ValueError):
        md.table_of_contents("# Heading", **{argument: value})


def test_table_of_contents_labels_are_plain_escaped_text():
    assert md.table_of_contents("# `a[b]` & `*x*`") == (
        "- [a\\[b\\] &amp; \\*x\\*](#ab--x)\n"
    )


@pytest.mark.parametrize("source, expected", [
    ("# Heading <!-- hidden -->", "- [Heading](#heading)\n"),
    ("# A <!-- hidden --> B", "- [A  B](#a--b)\n"),
    ("# A <!-- hidden\n# Hidden\n-->\n# B", "- [A](#a)\n- [B](#b)\n"),
    ("# `<!-- sample -->`", "- [&lt;!-- sample --&gt;](#---sample---)\n"),
])
def test_table_of_contents_inline_comments(source, expected):
    assert md.table_of_contents(source) == expected
