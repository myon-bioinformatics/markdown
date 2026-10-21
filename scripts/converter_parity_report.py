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
from scripts.converter_cases import arguments, select_keys


SYNTHETIC_CASES = {
    "basic_blocks": (
        "<h1>Title</h1><p>Hello <strong>world</strong> and "
        '<a href="https://example.com">link</a>.</p>'
    ),
    "lists": "<ul><li>one</li><li><ol><li>nested</li></ol></li></ul>",
    "blockquote": "<blockquote><p>Quoted <strong>text</strong>.</p></blockquote>",
    "inline_code": "<p>Use <code>print(1)</code> here.</p>",
    "preformatted_code": "<pre><code>def hello():\n    return 1\n</code></pre>",
    "alt_only_image": '<img alt="description">',
    "safe_relative_image": '<img src="/missing.png" alt="description">',
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


def case_keys():
    return ([f'html:{key}' for key in SYNTHETIC_CASES]
            + [f'html:{path.stem}' for path in sorted((ROOT / 'fixtures/benchmark').glob('*.html'))])


def collect_report(*, patterns=('*',), exclude=()) -> dict[str, Any]:
    patterns, exclude = tuple(patterns) if not isinstance(patterns, str) else patterns, tuple(exclude) if not isinstance(exclude, str) else exclude
    selected = set(select_keys(case_keys(), patterns, exclude))
    cases: list[dict[str, Any]] = []

    for case_id, html in SYNTHETIC_CASES.items():
        if 'html:' + case_id not in selected:
            continue
        cases.append(_record(case_id, "synthetic", html))

    benchmark_dir = ROOT / "fixtures" / "benchmark"
    real_world_paths = [path for path in sorted(benchmark_dir.glob("*.html")) if "html:" + path.stem in selected]
    for path in real_world_paths:
        html = path.read_text(encoding="utf-8")
        cases.append(_record(path.stem, str(path.relative_to(ROOT)), html))

    mismatches = [case["id"] for case in cases if not case["equal"]]
    real_world_case_count = len(real_world_paths)
    if mismatches:
        decision_hint = "investigate_mismatches_before_dom_first"
    elif real_world_case_count < 2:
        decision_hint = "expand_real_world_corpus_before_dom_first"
    else:
        decision_hint = "candidate_for_dom_first_evaluation"

    report = {
        "schema_version": 2,
        "case_count": len(cases),
        "match_count": len(cases) - len(mismatches),
        "mismatch_count": len(mismatches),
        "mismatch_ids": mismatches,
        "real_world_case_count": real_world_case_count,
        "corpus_note": (
            "Real-world HTML coverage is intentionally reported separately; "
            "fewer than two vendored pages is too thin for a DOM-first decision."
        ),
        "decision_hint": decision_hint,
        "cases": cases,
    }

    if patterns != ('*',) or exclude:
        report['selection'] = {'scope': 'selected_cases', 'patterns': list(patterns),
                               'exclude': list(exclude), 'selected': len(selected), 'available': len(case_keys())}
        report['decision_hint'] = 'selected_cases_only'
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out")
    arguments(parser)
    args = parser.parse_args(argv)

    try:
        patterns, exclude = args.case or ('*',), args.exclude or ()
        if args.list:
            if args.out is not None:
                parser.error('--list cannot be combined with --out')
            print(json.dumps({'cases': select_keys(case_keys(), patterns, exclude)}))
            return 0
        report = collect_report(patterns=patterns, exclude=exclude)
    except (OSError, ValueError) as error:
        print(f'error: {error}', file=sys.stderr)
        return 2
    out = Path(args.out or "converter_parity.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        f"cases={report['case_count']} "
        f"matches={report['match_count']} "
        f"mismatches={report['mismatch_count']} "
        f"real_world={report['real_world_case_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
