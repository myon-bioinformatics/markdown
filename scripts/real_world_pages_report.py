"""Build a static GitHub Pages report for the real-world HTML benchmark.

For every ``.html`` entry under ``fixtures/provenance.yaml``'s
``benchmark_fixtures`` list (see ``tests/test_benchmark_html_roundtrip.py``
for the assertions this data backs), this writes a small offline report
tree: the vendored original, its ``html_to_markdown()`` conversion, the
round-tripped HTML, and a before/after construct count -- plus, when
Playwright is installed, a screenshot of the original and the round trip
side by side, via ``python -m playwright screenshot`` (the CLI, same as
``tests/frontend/test_markdown_html_playwright_cli.py`` -- no
``sync_playwright()`` script here either).

Everything here runs on the vendored fixture only -- no live network
fetch of the real site. That keeps it reproducible (same bet every other
fixture in this repo already makes: a pinned snapshot, not a live re-fetch
that could drift or flake) and lets it run in CI with no external
dependency beyond Playwright's own browser download.

    python scripts/real_world_pages_report.py --out _site
"""

from __future__ import annotations

import argparse
import html as html_module
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import markdown as md

_TAG_COUNT_RES = {
    "h1": re.compile(r"<h1\b"),
    "h2": re.compile(r"<h2\b"),
    "a": re.compile(r"<a\b"),
    "img": re.compile(r"<img\b"),
}


def _load_html_fixtures() -> list[dict[str, Any]]:
    provenance = yaml.safe_load((ROOT / "fixtures" / "provenance.yaml").read_text(encoding="utf-8"))
    return [entry for entry in provenance["benchmark_fixtures"] if entry["path"].endswith(".html")]


def _raw_tag_counts(html: str) -> dict[str, int]:
    return {name: len(pattern.findall(html)) for name, pattern in _TAG_COUNT_RES.items()}


def _screenshot(file_uri: str, png_path: Path) -> bool:
    """Best-effort: True on success, False if Playwright/its browser isn't available."""
    result = subprocess.run(
        [sys.executable, "-m", "playwright", "screenshot", "--full-page", file_uri, str(png_path)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    return result.returncode == 0 and png_path.is_file()


def build_report(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    fixtures = _load_html_fixtures()
    rows: list[dict[str, Any]] = []

    for entry in fixtures:
        fixture_id = entry["id"]
        original_html = (ROOT / "fixtures" / entry["path"]).read_text(encoding="utf-8")
        converted_markdown = md.html_to_markdown(original_html)
        roundtrip_body = md.markdown_to_html(converted_markdown)
        roundtrip_html = f"<!doctype html><html><body>{roundtrip_body}</body></html>\n"

        case_dir = out_dir / fixture_id
        case_dir.mkdir(parents=True, exist_ok=True)
        (case_dir / "original.html").write_text(original_html, encoding="utf-8")
        (case_dir / "converted.md").write_text(converted_markdown, encoding="utf-8")
        (case_dir / "roundtrip.html").write_text(roundtrip_html, encoding="utf-8")

        before = _raw_tag_counts(original_html)
        after = _raw_tag_counts(roundtrip_html)
        stats = {"id": fixture_id, "source": entry["source"], "before": before, "after": after}
        (case_dir / "stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        has_original_png = _screenshot((case_dir / "original.html").as_uri(), case_dir / "original.png")
        has_roundtrip_png = _screenshot((case_dir / "roundtrip.html").as_uri(), case_dir / "roundtrip.png")
        rows.append({**stats, "has_original_png": has_original_png, "has_roundtrip_png": has_roundtrip_png})

    (out_dir / "index.html").write_text(_report_html(rows), encoding="utf-8")


def _report_html(rows: list[dict[str, Any]]) -> str:
    # No authored CSS: a plain semantic page, same bet this project's own
    # sibling report (mcp-toolcall-lab's GitHub Pages stub) already made --
    # https://abehiroshi.la.coocan.jp/-tier minimalism, not a design pass.
    sections = []
    for row in rows:
        fixture_id = row["id"]
        before, after = row["before"], row["after"]
        table_rows = "".join(
            f"<tr><td>{html_module.escape(tag)}</td><td>{before.get(tag, 0)}</td><td>{after.get(tag, 0)}</td></tr>"
            for tag in ("h1", "h2", "a", "img")
        )
        original_img = (
            f'<img src="{fixture_id}/original.png" alt="original {html_module.escape(fixture_id)}" width="480">'
            if row["has_original_png"]
            else "<p>(screenshot unavailable -- Playwright/its browser wasn't installed for this run)</p>"
        )
        roundtrip_img = (
            f'<img src="{fixture_id}/roundtrip.png" alt="round-tripped {html_module.escape(fixture_id)}" width="480">'
            if row["has_roundtrip_png"]
            else "<p>(screenshot unavailable -- Playwright/its browser wasn't installed for this run)</p>"
        )
        sections.append(
            f"<h2>{html_module.escape(fixture_id)}</h2>"
            f"<p>Source: {html_module.escape(row['source'])}</p>"
            f"<table><tr><th>tag</th><th>original</th><th>round-tripped</th></tr>{table_rows}</table>"
            f"<h3>Original (vendored fixture)</h3>{original_img}"
            f"<h3>Round-tripped (html_to_markdown -&gt; markdown_to_html)</h3>{roundtrip_img}"
            f'<p><a href="{fixture_id}/converted.md">converted.md</a> · '
            f'<a href="{fixture_id}/original.html">original.html</a> · '
            f'<a href="{fixture_id}/roundtrip.html">roundtrip.html</a></p>'
        )
    body = "".join(sections) or "<p>No .html benchmark fixtures found.</p>"
    return (
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        "<title>markdown.py: real-world HTML benchmark</title></head><body>"
        "<h1>real-world HTML -&gt; html_to_markdown() -&gt; markdown_to_html()</h1>"
        "<p>Every fixture here is a real, vendored page (see "
        "<code>fixtures/provenance.yaml</code>) run through both conversions, "
        "offline -- no live fetch of the real site happens in this report. "
        "See <code>tests/test_benchmark_html_roundtrip.py</code> for the exact "
        "construct-count assertions this data backs.</p>"
        f"{body}</body></html>\n"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="_site")
    args = parser.parse_args(argv)
    build_report(Path(args.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
