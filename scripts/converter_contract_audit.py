"""Audit converter contracts without changing runtime behavior.

This report is broader than converter_parity_report.py: it records several
HTML/Markdown/DOM paths and highlights where round trips are stable or
divergent. It is an observation tool for deciding follow-up PRs, not a
requirement that every path become lossless.

Usage:
    python scripts/converter_contract_audit.py --out converter_contract_audit.json
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


HTML_CASES = {
    "basic_blocks": "<h1>Title</h1><p>Hello <strong>world</strong>.</p>",
    "links_images": '<p><a href="https://example.com">docs</a> <img src="/img.png" alt="pic"></p>',
    "mixed_lists": "<ul><li>one</li><li><ol><li>nested</li></ol></li></ul>",
    "table": "<table><tr><th>a</th><th>b</th></tr><tr><td>1</td><td>2</td></tr></table>",
    "details": "<details><summary>More</summary><p>Body</p></details>",
    "task": '<ul><li><input type="checkbox" checked disabled> done</li></ul>',
    "attributes": '<h2 id="x" class="note">Title</h2><p data-kind="demo">Body</p>',
    "malformed": "<div><p>hello<strong> world</div>",
    "unicode": "<p>日本語 <strong>世界</strong> café</p>",
    "unsafe_url": '<p><a href="javascript:alert(1)">click</a></p>',
    "empty": "",
}

MARKDOWN_CASES = {
    "basic_blocks": "# Title\n\nHello **world**.\n",
    "links_images": "[docs](https://example.com) ![pic](/img.png)\n",
    "mixed_lists": "- one\n- two\n  1. nested\n",
    "table": "| a | b |\n| --- | --- |\n| 1 | 2 |\n",
    "details": ":::details More\nBody\n:::\n",
    "task": "- [x] done\n",
    "blockquote": "> quoted\n",
    "footnote": "Text[^1]\n\n[^1]: note\n",
    "attributes": "## Title {#x .note}\n\nBody\n",
    "unicode": "日本語 **世界** café\n",
    "empty": "",
}


# Exact Markdown footnote syntax is intentionally not reconstructed by
# html_to_markdown(). markdown_to_html() lowers [^id] refs/definitions to
# ordinary HTML anchors + a footnotes section, so an exact textual round trip
# is lossy by design. Keep that known loss visible without counting it as an
# unexpected converter divergence.
EXPECTED_LOSSY_CASES = {
    "markdown:footnote": (
        "Markdown footnote refs/definitions are lowered to HTML anchors and a "
        "footnotes section; html_to_markdown does not reconstruct [^id] syntax."
    ),
}


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _text_record(value: str) -> dict[str, Any]:
    return {
        "chars": len(value),
        "sha256": _sha256(value),
        "preview": value[:240],
    }


def _html_record(case_id: str, html: str, source: str = "synthetic") -> dict[str, Any]:
    legacy_md = md.html_to_markdown(html)
    dom_md = md.dom_to_markdown(md.parse_html_dom(html))

    legacy_back_html = md.markdown_to_html(legacy_md)
    legacy_back_md = md.html_to_markdown(legacy_back_html)

    dom_back_dom = md.markdown_to_dom(dom_md)
    dom_back_md = md.dom_to_markdown(dom_back_dom)

    checks = {
        "legacy_dom_equal": legacy_md == dom_md,
        "legacy_md_html_md_stable": legacy_md == legacy_back_md,
        "dom_md_dom_md_stable": dom_md == dom_back_md,
    }
    return {
        "id": case_id,
        "kind": "html",
        "source": source,
        "checks": checks,
        "all_checks_pass": all(checks.values()),
        "input": _text_record(html),
        "legacy_markdown": _text_record(legacy_md),
        "dom_markdown": _text_record(dom_md),
    }


def _markdown_record(case_id: str, markdown: str) -> dict[str, Any]:
    html = md.markdown_to_html(markdown)
    html_back_md = md.html_to_markdown(html)

    dom = md.markdown_to_dom(markdown)
    dom_back_md = md.dom_to_markdown(dom)

    checks = {
        "md_html_md_stable": markdown == html_back_md,
        "md_dom_md_stable": markdown == dom_back_md,
    }
    return {
        "id": case_id,
        "kind": "markdown",
        "source": "synthetic",
        "checks": checks,
        "all_checks_pass": all(checks.values()),
        "input": _text_record(markdown),
        "html_back_markdown": _text_record(html_back_md),
        "dom_back_markdown": _text_record(dom_back_md),
    }


def collect_report() -> dict[str, Any]:
    cases: list[dict[str, Any]] = []

    for case_id, html in HTML_CASES.items():
        cases.append(_html_record(case_id, html))

    for case_id, markdown in MARKDOWN_CASES.items():
        cases.append(_markdown_record(case_id, markdown))

    benchmark_dir = ROOT / "fixtures" / "benchmark"
    real_world_paths = sorted(benchmark_dir.glob("*.html"))
    for path in real_world_paths:
        cases.append(
            _html_record(
                path.stem,
                path.read_text(encoding="utf-8"),
                str(path.relative_to(ROOT)),
            )
        )

    raw_divergent: list[str] = []
    expected_lossy: list[str] = []
    divergent: list[str] = []

    for case in cases:
        case_key = f'{case["kind"]}:{case["id"]}'
        if case["all_checks_pass"]:
            case["classification"] = "stable"
            continue

        raw_divergent.append(case_key)
        reason = EXPECTED_LOSSY_CASES.get(case_key)
        if reason is not None:
            case["classification"] = "expected_lossy"
            case["expected_loss_reason"] = reason
            expected_lossy.append(case_key)
        else:
            case["classification"] = "divergent"
            divergent.append(case_key)

    return {
        "schema_version": 2,
        "case_count": len(cases),
        "stable_case_count": sum(
            case["classification"] == "stable" for case in cases
        ),
        "expected_lossy_case_count": len(expected_lossy),
        "divergent_case_count": len(divergent),
        "raw_divergent_case_ids": raw_divergent,
        "expected_lossy_case_ids": expected_lossy,
        "divergent_case_ids": divergent,
        "real_world_html_count": len(real_world_paths),
        "note": (
            "Exact round-trip loss is classified separately when it is an "
            "explicit converter contract (expected_lossy). Remaining "
            "divergence is observational and not automatically a bug."
        ),
        "cases": cases,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="converter_contract_audit.json")
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
        f"stable={report['stable_case_count']} "
        f"expected_lossy={report['expected_lossy_case_count']} "
        f"divergent={report['divergent_case_count']} "
        f"real_world={report['real_world_html_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
