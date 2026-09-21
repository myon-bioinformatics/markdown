"""Compare legacy and DOM-mediated HTML->Markdown conversion paths.

This is an evaluation tool, not a DOM-first switch. It runs both paths over
the same synthetic + vendored real-world corpus and writes a deterministic
JSON report so #40 can make an evidence-based decision.

Usage:
    python scripts/converter_parity_report.py --out converter_parity.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import markdown as md


SYNTHETIC_CASES = {
    "basic_blocks": (
        "<h1>Title</h1><p>Hello <strong>world</strong> and "
        '<a href="https://example.com">link</a>.</p>'
    ),
    "lists": "<ul><li>one</li><li><ol><li>nested</li></ol></li></ul>",
    "blockquote": "<blockquote><p>Quoted <strong>text</strong>.</p></blockquote>",
    "inline_code": "<p>Use <code>print(1)</code> here.</p>",
    "preformatted_code": "<pre><code>def hello():\n    return 1\n</code></pre>",
    "alt_only_image": '<img src="/missing.png" alt="description">',
    "table": (
        "<table><thead><tr><th>a</th><th>b</th></tr></thead>"
        "<tbody><tr><td>1</td><td>2</td></tr></tbody></table>"
    ),
    "details": "<details><summary>More</summary><p>Body <em>text</em>.</p></details>",
    "unsafe_link": '<a href="javascript:alert(1)">click</a>',
    "unsafe_image": '<img src="javascript:alert(1)" alt="pic">',
    "empty": "",
    "suppressed": "<script>alert(1)</script><style>x{}</style>",
    "unicode": "<p>日本語 <strong>世界</strong> café</p>",
    "host_port": '<a href="example.com:8080/path">host</a>',
}


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _record(case_id: str, source: str, html: str) -> dict[str, Any]:
    legacy = md.html_to_markdown(html)
    dom = md.dom_to_markdown(md.parse_html_dom(html))
    equal = legacy == dom
    record: dict[str, Any] = {
        "id": case_id,
        "source": source,
        "equal": equal,
        "input_chars": len(html),
        "legacy_chars": len(legacy),
        "dom_chars": len(dom),
        "legacy_sha256": _sha256(legacy),
        "dom_sha256": _sha256(dom),
    }
    if not equal:
        record["legacy_preview"] = legacy[:500]
        record["dom_preview"] = dom[:500]
    return record


def collect_report() -> dict[str, Any]:
    cases: list[dict[str, Any]] = []

    for case_id, html in SYNTHETIC_CASES.items():
        cases.append(_record(case_id, "synthetic", html))

    benchmark_dir = ROOT / "fixtures" / "benchmark"
    for path in sorted(benchmark_dir.glob("*.html")):
        html = path.read_text(encoding="utf-8")
        cases.append(_record(path.stem, str(path.relative_to(ROOT)), html))

    mismatches = [case["id"] for case in cases if not case["equal"]]
    return {
        "schema_version": 1,
        "case_count": len(cases),
        "match_count": len(cases) - len(mismatches),
        "mismatch_count": len(mismatches),
        "mismatch_ids": mismatches,
        "decision_hint": (
            "candidate_for_dom_first_evaluation"
            if not mismatches
            else "investigate_mismatches_before_dom_first"
        ),
        "cases": cases,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="converter_parity.json")
    args = parser.parse_args(argv)

    report = collect_report()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        f"cases={report['case_count']} "
        f"matches={report['match_count']} "
        f"mismatches={report['mismatch_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
