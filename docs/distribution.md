# Distribution and vendoring

The project has two deliberately different identities:

| Context | Name |
| --- | --- |
| Canonical single-file source | `markdown.py` |
| Vendored consumer path | `vendor/markdown.py` |
| Standalone use | copy `markdown.py` from GitHub |
| Planned PyPI distribution | `md-market` |
| uv git distribution | `md-market` (no runtime dependencies) |
| Python module/file | `markdown.py` |

## Why keep `markdown.py` for vendoring?

The repository is already built and tested around a single-file artifact. A consumer such as Ironmate can copy that artifact into `vendor/markdown.py` and audit the exact source revision without adding a runtime package dependency.

Standalone users copy the file from GitHub. The copied `markdown.py` stays standard-library only and keeps working on its own.

## Why use `md-market` for PyPI?

`md-market` is the distribution name only. The implementation remains the stdlib-only single file `markdown.py`, so local use, direct copying, and vendoring all share the same actual artifact.

## Packaging rule

The repository root is an installable uv project named `md-market`. It packages the existing `markdown.py` artifact and has no runtime dependencies. There is still one source of truth: the single stdlib-only module. Standalone users copy the file from GitHub instead of installing the project.
