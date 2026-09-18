"""CommonMark spec examples as a stress test -- not a compliance claim.

Loads fixtures/benchmark/commonmark_examples.yaml (13 of the official
CommonMark spec's own numbered examples) and asserts markdown_to_html()'s
*current* output for each matches the recorded ``our_html`` baseline. This
module isn't a full CommonMark engine (see markdown.py's own SUPPORTED /
UNSUPPORTED), so several of these are expected, recorded FAILs -- that's
the point: this is a regression pin on "what we know doesn't work today",
not an aspiration that everything here passes.

If markdown.py's parsing genuinely changes (a real fix, not an accident),
update the matching ``our_html`` / ``classification`` in the YAML deliberately
-- a diff there is a design decision, not something to silence.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import markdown as md

FIXTURES = ROOT / "fixtures" / "benchmark"
VALID_CLASSIFICATIONS = {"PASS", "DEGRADED", "UNSUPPORTED", "FAIL"}


def _load_examples() -> list[dict]:
    data = yaml.safe_load((FIXTURES / "commonmark_examples.yaml").read_text(encoding="utf-8"))
    return data["examples"]


EXAMPLES = _load_examples()


def test_commonmark_examples_file_is_well_formed() -> None:
    assert len(EXAMPLES) >= 10
    seen_ids = set()
    for ex in EXAMPLES:
        assert ex["classification"] in VALID_CLASSIFICATIONS, ex["id"]
        assert ex["id"] not in seen_ids, f"duplicate id: {ex['id']}"
        seen_ids.add(ex["id"])
        assert isinstance(ex["spec_example"], int)
        assert ex["markdown"]
        assert ex["commonmark_html"]
        assert ex["our_html"]


@pytest.mark.parametrize("example", EXAMPLES, ids=[ex["id"] for ex in EXAMPLES])
def test_recorded_output_matches_current_behavior(example: dict) -> None:
    """Regression pin: today's markdown_to_html() output must match what was recorded."""
    actual = md.markdown_to_html(example["markdown"]).rstrip("\n")
    assert actual == example["our_html"], (
        f"{example['id']} (spec example {example['spec_example']}): "
        f"behavior changed -- update commonmark_examples.yaml deliberately if this is a real fix"
    )


@pytest.mark.parametrize(
    "example",
    [ex for ex in EXAMPLES if ex["classification"] == "PASS"],
    ids=[ex["id"] for ex in EXAMPLES if ex["classification"] == "PASS"],
)
def test_pass_classified_examples_actually_match_commonmark(example: dict) -> None:
    """Anything marked PASS must genuinely match the spec's own expected HTML."""
    actual = md.markdown_to_html(example["markdown"]).rstrip("\n")
    assert actual == example["commonmark_html"], example["id"]


def test_at_least_one_example_per_requested_category() -> None:
    requested = {
        "headings",
        "emphasis",
        "nested_emphasis",
        "escaping",
        "blockquote",
        "nested_list",
        "fenced_code",
        "inline_code",
        "horizontal_rule",
        "links",
        "edge_cases",
    }
    covered = {ex["category"] for ex in EXAMPLES}
    missing = requested - covered
    assert not missing, f"no CommonMark example for: {missing}"


def test_classification_summary_is_printable() -> None:
    """Not a real assertion -- keeps the human-readable summary from ``pytest -s`` handy."""
    counts: dict[str, int] = {}
    for ex in EXAMPLES:
        counts[ex["classification"]] = counts.get(ex["classification"], 0) + 1
    lines = [f"  {k}: {v}" for k, v in sorted(counts.items())]
    summary = "CommonMark benchmark classification counts:\n" + "\n".join(lines)
    print("\n" + summary)
    assert sum(counts.values()) == len(EXAMPLES)
