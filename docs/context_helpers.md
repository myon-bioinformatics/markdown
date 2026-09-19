# Markdown context helpers

PR #12 adds four small, deterministic helpers for preparing Markdown before it
is shown to an LLM or a chat UI. They are intentionally heuristic utilities,
not a CommonMark parser and not a summarizer.

- extract_section(content, heading_name, level=None, partial=False) returns
  one ATX heading and its nested children, stopping at the next heading at the
  same or a higher level.
- strip_prose_keep_structure(content) keeps headings, lists, blockquotes,
  thematic breaks, and fenced code while dropping ordinary prose lines. It does
  not call an LLM or summarize text.
- minify_markdown(content, strip_html=True) removes HTML comments when
  requested, collapses runs of blank lines, and strips surrounding whitespace.
- safe_truncate(content, max_chars) enforces a hard character limit and closes
  an open fenced block when there is room to do so.

These helpers do not add runtime dependencies, fetch URLs, define a chat
history format, or introduce a protocol/schema. Conversation compression,
key/value parsing rules, and broader HTML conversion remain separate future
design topics.
