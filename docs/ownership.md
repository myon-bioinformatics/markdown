# Extension ownership

`markdown.py` remains one stdlib-only module. To keep parallel pull requests
mergeable, new conversion work belongs to one declared section and must not
reformat unrelated code or reorder existing exports.

| Section | Current scope | Rule for new work |
| --- | --- | --- |
| `scanner` | `_scan_lines`, `_mask_inline_code`, fence state | Reuse it for code-context decisions; do not widen it into a CommonMark parser. |
| extraction | `extract_*`, `inventory`, context helpers | Add a focused extractor and its contract tests. |
| conversion | HTML, Kramdown, dialect helpers, structured data core/adapters | Declare the source/target subset and lossiness; INI/TOML/dotenv reuse structured_to_markdown / markdown_to_structured and keep canonical round-trip contracts explicit. |
| generation | Markdown builders | Keep output deterministic and testable without a renderer. |
| tables | GFM table generators/conversion | Add width/CSV/statistics work here. |
| `directory tree` | directory listing / `tree` text <-> nested Markdown list, scaffold creation | Names are validated before any filesystem write; never overwrite existing files. |
| `markdown lite model` | `_lite_blocks` / `_lite_inline` shared by one-way and dialect writers | Extend the shared tokenizer instead of adding a per-format Markdown parser. |
| `system formats` | calendar / platform tables, email <-> Markdown, Markdown -> man | No I/O beyond the inputs given; never send mail or decode attachments to disk. |
| `dialects` | Slack mrkdwn / Org / MediaWiki / Jira <-> Markdown, chat messages <-> `## Role` | Declare the canonical subset each dialect round-trips on; keep code spans/links placeholder-protected. |
| `llm io` | `split_reasoning` / `compact_llm_output` / `llm_output_digest` / `extract_identifiers` | Reuse the shared scanner/masking helpers and the `extract_*` family for code-context and structure; keep reasoning-tag and identifier detection a declared, narrow heuristic, not a provider-format parser. |

`__all__` is maintained one entry per line. Add a public name adjacent to its
functional peers; do not perform a repository-wide reordering in a feature PR.
