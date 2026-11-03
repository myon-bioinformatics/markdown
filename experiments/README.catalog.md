# Real-world catalog integration experiment (not adopted)

Proposed independent Draft PR target: `myon-bioinformatics/markdown`, based on
`8590570dd5af8c9ed132186e11a2521546ac83ea`.
Only these four files under `experiments/` are added. No workflow, dependency,
vendor lock, report producer, existing index, public URL or deployment is changed.
web-ui #111 stays Draft and unmerged. Do not deploy this experiment.

The adapter reads the existing generated `index.html`, fixture `stats.json`, and
`build_meta.json`. The current index's `original.html` links define the fixture
set, so leftover directories from older runs do not become current results.
Counts are read from stats without recomputation or fabricated defaults; revision
metadata is reproduced as recorded, including nulls and dirty status. Each card
links to converted Markdown, roundtrip HTML, original HTML, stats JSON, the existing
report with tables/images, and build metadata. Images are linked only when both
advertised by the current report and present on disk. Unadvertised stale PNGs are
omitted. Missing required/advertised evidence and paths escaping the report root
fail before any output is written. Text is escaped by the pinned common renderer.

## Explicit local execution

Obtain `web_ui.py` from web-ui commit
`96079aba4084e11834c4d9c70d40eea3f5b326bd` into a separate local path (not vendor).
The adapter checks SHA-256
`75531bd58c523a6e5ecc92580f78d012e6747e927dcfd4887c9314b10c8e8a0b`
before loading it. There is no network fetch or fallback renderer in the adapter.
This executable file is a trusted, fixed experimental dependency, not arbitrary input.

From the markdown checkout:

```sh
python scripts/real_world_pages_report.py --out /tmp/markdown-catalog-report
python -S experiments/real_world_catalog.py \
  --report /tmp/markdown-catalog-report --web-ui /absolute/path/web_ui.py
CATALOG_WEB_UI=/absolute/path/web_ui.py python -m unittest discover \
  -s experiments -p test_real_world_catalog.py -v
python experiments/check_catalog_browser.py --report /tmp/markdown-catalog-report \
  --chromium /absolute/path/chromium --screenshots /tmp/catalog-browser-check
```

Only `catalog-experiment.html` is written by the adapter, beside the existing
report. The final write uses atomic replacement and rejects a symlink destination.
It never overwrites report evidence or runs the report builder itself. The adapter
and renderer need only Python's standard library; the existing report builder
still has its existing PyYAML/browser tooling requirements. Browser verification
is opt-in and requires Playwright and an explicitly selected Chromium executable.

## Local verification, 2026-11-03

- One real vendored HTML fixture, `tohoho_web_home`, was run through the existing
  report generator. Both before and after: h1=1, h2=24, a=263, img=2. These are
  tag counts, not screenshot counts, quality scores, or live-site measurements.
- The recorded revision is `8590570d`, branch main, dirty=true. Dirty=true
  truthfully includes the local untracked experimental files. No revision was
  fabricated to look clean. Version and commit URL are null in this environment.
- The report generator's screenshot attempts failed because its expected
  Playwright browser executable was absent. Both PNG links were therefore omitted.
  Synthetic tests separately cover present/absent/stale/advertised-missing PNGs.
- 7 adapter tests passed. 20 existing report/screenshot-evidence tests passed;
  3 existing repository-history-dependent tests skipped. Synthetic edge-case
  tests are labeled as such and are never reported as measured results.
- Chromium, JavaScript disabled: HTTP project subpath and file URLs at widths
  320, 390, 1440 all passed (6 conditions). Verified no horizontal page overflow,
  keyboard disclosure, local link targets, and navigation to roundtrip/stats.
  The 390px capture was also visually inspected. These are local browser checks;
  hosted GitHub CI has not been run for this proposal.
- Navigation to the existing roundtrip page exposes two already missing local
  source image assets (`image/tohoho.gif`, `image/popase.gif`). This experiment
  preserves that report exactly and does not claim those source assets exist.
- Two adapter runs produced byte-identical HTML. Hashes of every other generated
  report file, including index.html, remained unchanged. `git diff --check` passed.

No push, PR creation, merge, formal adoption or publication has been performed.
External changes require user approval. Proposed PR title:
`Experiment: index existing real-world report with pinned web-ui catalog`.
