# Extension ownership

`markdown.py` remains one stdlib-only module. To keep parallel pull requests
mergeable, new conversion work belongs to one declared section and must not
reformat unrelated code or reorder existing exports.

| Section | Current scope | Rule for new work |
| --- | --- | --- |
| `scanner` | `_scan_lines`, `_mask_inline_code`, fence state | Reuse it for code-context decisions; do not widen it into a CommonMark parser. |
| extraction | `extract_*`, `inventory`, context helpers, `_mask_code_context`, `classify_data_uri` | Add a focused extractor and its contract tests. Reuse `_mask_code_context` so fenced/inline code stays excluded consistently. |
| conversion | HTML, Kramdown and dialect helpers | Declare the source/target subset and lossiness. |
| generation | Markdown builders | Keep output deterministic and testable without a renderer. |
| tables | GFM table generators/conversion | Add width/CSV/statistics work here. |

`__all__` is maintained one entry per line. Add a public name adjacent to its
functional peers; do not perform a repository-wide reordering in a feature PR.
