# Distribution and vendoring

The project has two deliberately different identities:

| Context | Name |
| --- | --- |
| Canonical single-file source | `markdown.py` |
| Vendored consumer path | `vendor/markdown.py` |
| Planned PyPI distribution | `md-market` |
| Python module/file | `markdown.py` |

## Why keep `markdown.py` for vendoring?

The repository is already built and tested around a single-file artifact. A consumer such as Ironmate can copy that artifact into `vendor/markdown.py` and audit the exact source revision without adding a runtime package dependency.

## Why use `md-market` for PyPI?

`md-market` is the distribution name only. The implementation remains the stdlib-only single file `markdown.py`, so local use, direct copying, and vendoring all share the same actual artifact.

## Packaging rule

Any future PyPI packaging should package the existing `markdown.py` artifact without creating a second implementation file. The project should retain one source of truth: the single stdlib-only module.
