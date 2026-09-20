# Extension ownership

`markdown.py` remains one stdlib-only module. To keep parallel pull requests
mergeable, new conversion work belongs to one declared section and must not
reformat unrelated code or reorder existing exports.

| Section | Current scope | Rule for new work |
| --- | --- | --- |
| `scanner` | `_scan_lines`, `_mask_inline_code`, fence state | Reuse it for code-context decisions; do not widen it into a CommonMark parser. |
| extraction | `extract_*`, `inventory`, context helpers | Add a focused extractor and its contract tests. |
| conversion | HTML, Kramdown and dialect helpers | Declare the source/target subset and lossiness. |
| generation | Markdown builders | Keep output deterministic and testable without a renderer. |
| tables | GFM table generators/conversion; `markdown_table_to_rows`/`markdown_table_to_records`/`markdown_table_to_csv`/`csv_to_markdown_table`; `table(..., align=True)` + `east_asian_width` | Statistics summaries are still open; add them here too. |

`__all__` is maintained one entry per line. Add a public name adjacent to its
functional peers; do not perform a repository-wide reordering in a feature PR.
