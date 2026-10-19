"""Tests for slugify and table_of_contents functions in markdown.py."""

import pytest
import markdown as md


def test_slugify_basic():
    assert md.slugify("Hello World!") == "hello-world"
    assert md.slugify("User & Permissions (v2.0)") == "user-permissions-v20"
    assert md.slugify("  Spaces   And\tTabs  ") == "spaces-and-tabs"


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
