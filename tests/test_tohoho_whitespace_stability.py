from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import markdown as md

TOHOHO = ROOT / "fixtures" / "benchmark" / "tohoho_web_home.html"


def _first_diff(left: str, right: str) -> tuple[int, str, str]:
    index = next(
        (i for i, (a, b) in enumerate(zip(left, right)) if a != b),
        min(len(left), len(right)),
    )
    lo = max(0, index - 100)
    hi = index + 100
    return index, repr(left[lo:hi]), repr(right[lo:hi])


def test_tohoho_markdown_is_stable_after_html_round_trip() -> None:
    html = TOHOHO.read_text(encoding="utf-8")
    first = md.html_to_markdown(html)
    second = md.html_to_markdown(md.markdown_to_html(first))

    assert first == second, _first_diff(first, second)


def test_tohoho_dom_markdown_is_stable_after_dom_round_trip() -> None:
    html = TOHOHO.read_text(encoding="utf-8")
    first = md.dom_to_markdown(md.parse_html_dom(html))
    second = md.dom_to_markdown(md.markdown_to_dom(first))

    assert first == second, _first_diff(first, second)
