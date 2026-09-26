from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import markdown as md

CANONICAL = """# Title

Intro with **bold**, *italic*, ~~gone~~, `code`, and [a link](https://example.com).

## Section

- item one
  - nested item
    1. deep ordered
- item two

1. first
2. second

> quoted line

```python
print("hi")
```

---
"""

DIALECTS = {
    "org": (md.markdown_to_org, md.org_to_markdown),
    "mediawiki": (md.markdown_to_mediawiki, md.mediawiki_to_markdown),
    "jira": (md.markdown_to_jira, md.jira_to_markdown),
}


def test_exports() -> None:
    for name in (
        "markdown_to_slack_mrkdwn",
        "slack_mrkdwn_to_markdown",
        "chat_messages_to_markdown",
        "markdown_to_chat_messages",
        "markdown_to_org",
        "org_to_markdown",
        "markdown_to_mediawiki",
        "mediawiki_to_markdown",
        "markdown_to_jira",
        "jira_to_markdown",
        "CHAT_ROLES",
    ):
        assert name in md.__all__


@pytest.mark.parametrize("name", sorted(DIALECTS))
def test_canonical_markdown_round_trips(name: str) -> None:
    to_dialect, to_markdown = DIALECTS[name]
    assert to_markdown(to_dialect(CANONICAL)) == CANONICAL


@pytest.mark.parametrize("name", sorted(DIALECTS))
def test_dialect_output_is_a_fixed_point(name: str) -> None:
    to_dialect, to_markdown = DIALECTS[name]
    once = to_dialect(CANONICAL)
    assert to_dialect(to_markdown(once)) == once


@pytest.mark.parametrize("name", sorted(DIALECTS) + ["slack"])
def test_empty_input(name: str) -> None:
    to_dialect, to_markdown = DIALECTS.get(name, (md.markdown_to_slack_mrkdwn, md.slack_mrkdwn_to_markdown))
    assert to_dialect("") == ""
    assert to_markdown("") == ""


def test_markup_inside_code_is_never_converted() -> None:
    source = "Use `**not bold**` and `[x](y)`.\n\n```\n**raw** *raw*\n```\n"
    for name, (to_dialect, to_markdown) in DIALECTS.items():
        assert to_markdown(to_dialect(source)) == source, name


# --- Org ----------------------------------------------------------------------

def test_org_forward_shapes() -> None:
    out = md.markdown_to_org(CANONICAL)
    assert "* Title" in out.splitlines()
    assert "** Section" in out.splitlines()
    assert "Intro with *bold*, /italic/, +gone+, ~code~, and [[https://example.com][a link]]." in out
    assert "#+BEGIN_SRC python" in out and "#+END_SRC" in out
    assert "#+BEGIN_QUOTE\nquoted line\n#+END_QUOTE" in out
    assert "1. first\n2. second" in out


def test_org_src_lines_starting_with_star_are_comma_escaped() -> None:
    source = "```\n* looks like a heading\n#+TITLE: x\n```\n"
    org = md.markdown_to_org(source)
    assert ",* looks like a heading" in org
    assert ",#+TITLE: x" in org
    assert md.org_to_markdown(org) == source


def test_org_reads_example_blocks_verbatim_and_plain_links() -> None:
    org = "#+begin_example\nkeep *this*\n#+end_example\nSee [[https://a.example]] and =verb=.\n"
    assert md.org_to_markdown(org) == "```\nkeep *this*\n```\nSee <https://a.example> and `verb`.\n"


def test_org_urls_in_text_are_not_read_as_italic() -> None:
    assert md.org_to_markdown("see https://a.example/b/c now\n") == "see https://a.example/b/c now\n"


# --- MediaWiki ----------------------------------------------------------------

def test_mediawiki_forward_shapes() -> None:
    out = md.markdown_to_mediawiki(CANONICAL)
    lines = out.splitlines()
    assert "= Title =" in lines and "== Section ==" in lines
    assert "Intro with '''bold''', ''italic'', <s>gone</s>, <code>code</code>, and [https://example.com a link]." in lines
    assert "* item one" in lines and "** nested item" in lines and "**# deep ordered" in lines
    assert '<syntaxhighlight lang="python">' in lines


def test_mediawiki_bold_italic_and_internal_links() -> None:
    wiki = "'''''both''''' and [[Main Page|home]] and [https://x.example]\n"
    assert md.mediawiki_to_markdown(wiki) == "***both*** and [[Main Page|home]] and <https://x.example>\n"


def test_mediawiki_pre_and_source_blocks() -> None:
    wiki = '<source lang="bash">\necho hi\n</source>\n<pre>\nplain\n</pre>\n'
    assert md.mediawiki_to_markdown(wiki) == "```bash\necho hi\n```\n```\nplain\n```\n"


# --- Jira ---------------------------------------------------------------------

def test_jira_forward_shapes() -> None:
    out = md.markdown_to_jira(CANONICAL)
    lines = out.splitlines()
    assert "h1. Title" in lines and "h2. Section" in lines
    assert "Intro with *bold*, _italic_, -gone-, {{code}}, and [a link|https://example.com]." in lines
    assert "{code:python}" in lines and "bq. quoted line" in lines


def test_jira_reads_code_options_noformat_quote_and_images() -> None:
    jira = (
        "{code:language=java|title=Demo}\nint x;\n{code}\n"
        "{noformat}\n*raw*\n{noformat}\n"
        "{quote}\nquoted *bold*\n{quote}\n"
        "!https://img.example/a.png|thumbnail! and - dash item\n"
    )
    assert md.jira_to_markdown(jira) == (
        "```java\nint x;\n```\n"
        "```\n*raw*\n```\n"
        "> quoted **bold**\n"
        "![](https://img.example/a.png) and - dash item\n"
    )


def test_jira_does_not_misread_ordinary_punctuation() -> None:
    text = "wow!great! 1-2-3 and a - b - c, well-known\n"
    assert md.jira_to_markdown(text) == text


def test_jira_dash_list_items() -> None:
    assert md.jira_to_markdown("- a\n- b\n") == "- a\n- b\n"


# --- Slack --------------------------------------------------------------------

SLACK_CANONICAL = """Intro with **bold**, *italic*, ~~gone~~, `code`, and [a link](https://example.com) & <https://x.y>.

- item one
  - nested item
- item two

1. first
2. second

> quoted line

```
if a < b && c > d:
```
"""


def test_slack_round_trip_on_its_subset() -> None:
    assert md.slack_mrkdwn_to_markdown(md.markdown_to_slack_mrkdwn(SLACK_CANONICAL)) == SLACK_CANONICAL


def test_slack_forward_shapes_and_escaping() -> None:
    out = md.markdown_to_slack_mrkdwn(SLACK_CANONICAL)
    assert "Intro with *bold*, _italic_, ~gone~, `code`, and <https://example.com|a link> &amp; <https://x.y>." in out
    assert "• item one\n    • nested item" in out
    assert "if a &lt; b &amp;&amp; c &gt; d:" in out


def test_slack_lossy_constructs_are_documented_shapes() -> None:
    out = md.markdown_to_slack_mrkdwn("# Head\n\n```python\nx\n```\n")
    assert out == "*Head*\n\n```\nx\n```\n"
    # A heading comes back as a bold paragraph; the fence language is gone.
    assert md.slack_mrkdwn_to_markdown(out) == "**Head**\n\n```\nx\n```\n"


def test_slack_mentions_stay_literal() -> None:
    assert md.slack_mrkdwn_to_markdown("hi <@U123> in <#C1|general> <!here>\n") == "hi <@U123> in <#C1|general> <!here>\n"


# --- Chat messages ------------------------------------------------------------

MESSAGES = [
    {"role": "system", "content": "Be terse."},
    {"role": "user", "content": "## Summary\nhi\n```\n## User\n```"},
    {"role": "assistant", "content": ""},
    {"role": "tool", "content": '{"ok": true}'},
]


def test_chat_messages_round_trip() -> None:
    rendered = md.chat_messages_to_markdown(MESSAGES)
    assert rendered.startswith("## System\n\nBe terse.\n\n## User\n\n## Summary\n")
    assert md.markdown_to_chat_messages(rendered) == MESSAGES
    assert md.chat_messages_to_markdown(md.markdown_to_chat_messages(rendered)) == rendered


def test_chat_headings_are_case_insensitive_and_other_headings_are_content() -> None:
    parsed = md.markdown_to_chat_messages("## USER\nhello\n## Notes\nmore\n## assistant\nok\n")
    assert parsed == [
        {"role": "user", "content": "hello\n## Notes\nmore"},
        {"role": "assistant", "content": "ok"},
    ]


@pytest.mark.parametrize(
    "messages",
    [
        [{"role": "user", "content": "hi", "name": "bob"}],
        [{"role": "robot", "content": "hi"}],
        [{"role": "user", "content": [{"type": "text", "text": "hi"}]}],
        [{"role": "user", "content": "before\n## Assistant\nafter"}],
        ["not a dict"],
    ],
)
def test_chat_rejects_unsupported_or_ambiguous_messages(messages: list) -> None:
    with pytest.raises(ValueError):
        md.chat_messages_to_markdown(messages)


def test_chat_rejects_text_before_first_role() -> None:
    with pytest.raises(ValueError, match="before the first role"):
        md.markdown_to_chat_messages("preamble\n## User\nhi\n")


def test_chat_roles_constant() -> None:
    assert md.CHAT_ROLES == ("system", "developer", "user", "assistant", "tool")
