# Distribution and vendoring

The project has two deliberately different identities:

| Context | Name |
| --- | --- |
| Canonical single-file source | `markdown.py` |
| Vendored consumer path | `vendor/markdown.py` |
| Planned PyPI distribution | `md-market` |
| Planned Python import | `md_market` |

## Why keep `markdown.py` for vendoring?

The repository is already built and tested around a single-file artifact. A consumer such as Ironmate can copy that artifact into `vendor/markdown.py` and audit the exact source revision without adding a runtime package dependency.

## Why use `md_market` for PyPI?

A published package should not unnecessarily occupy or conflict with the generic `markdown` import namespace. The package-facing name `md_market` gives this project a distinct identity while allowing the vendored artifact to keep the concise filename `markdown.py`.

## Packaging rule

Do not make the PyPI package by simply publishing the current file as top-level `markdown`. The eventual packaging PR should expose `import md_market` while preserving `markdown.py` as the canonical vendoring artifact and keeping the two surfaces synchronized by test or generation rather than manual duplication.
