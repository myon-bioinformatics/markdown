"""Contracts for the shared Markdown line scanner (Hub-P0)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import markdown as md


def test_scanner_marks_adaptive_fence_and_its_contents() -> None:
    lines = ["````markdown", "```nested", "```", "````", "outside"]
    scanned = md._scan_lines(lines)

    assert [line.in_fenced_code for line in scanned] == [True, True, True, True, False]
    assert [line.is_fence_open for line in scanned] == [True, False, False, False, False]
    assert [line.is_fence_close for line in scanned] == [False, False, False, True, False]


def test_scanner_handles_tilde_fences_independently() -> None:
    scanned = md._scan_lines(["~~~python", "```not a closer", "~~~", "text"])
    assert [line.in_fenced_code for line in scanned] == [True, True, True, False]
    assert scanned[2].is_fence_close


def test_inline_code_mask_preserves_offsets_and_ignores_unclosed_runs() -> None:
    source = "[live](https://example.test) and `[not](https://hidden.test)` plus `open"
    masked = md._mask_inline_code(source)

    assert len(masked) == len(source)
    assert "https://example.test" in masked
    assert "https://hidden.test" not in masked
    assert "`open" in masked


def test_extract_code_blocks_uses_the_shared_adaptive_fence_contract() -> None:
    source = "````markdown\n```inner\n```\n````\n"
    assert md.extract_code_blocks(source) == [
        {"language": "markdown", "info": "markdown", "code": "```inner\n```"}
    ]
