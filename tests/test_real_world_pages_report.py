"""Smoke tests for scripts/real_world_pages_report.py.

The GitHub Pages workflow runs:

    python scripts/real_world_pages_report.py --out _site

``_site`` is relative. ``Path.as_uri()`` raises ValueError on a relative
path, which is what broke run 35455946035 after PR #14. These tests pin
that the report resolves before taking a file URI, without requiring
Playwright or its browsers (screenshots are already best-effort).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _load_report_module():
    path = ROOT / "scripts" / "real_world_pages_report.py"
    spec = importlib.util.spec_from_file_location("real_world_pages_report", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_build_report_with_relative_out_does_not_raise_on_as_uri(tmp_path, monkeypatch) -> None:
    report = _load_report_module()
    monkeypatch.chdir(tmp_path)

    seen_uris: list[str] = []

    def fake_screenshot(file_uri: str, png_path: Path) -> bool:
        seen_uris.append(file_uri)
        parsed = urlparse(file_uri)
        assert parsed.scheme == "file", file_uri
        local = Path(unquote(parsed.path))
        assert local.is_absolute(), file_uri
        return False

    monkeypatch.setattr(report, "_screenshot", fake_screenshot)

    report.build_report(Path("_site"))

    assert (tmp_path / "_site" / "index.html").is_file()
    assert seen_uris
    assert all(uri.startswith("file://") for uri in seen_uris)
