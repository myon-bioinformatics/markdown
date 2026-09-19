"""Smoke tests for scripts/real_world_pages_report.py.

The GitHub Pages workflow runs:

    python scripts/real_world_pages_report.py --out _site

``_site`` is relative. ``Path.as_uri()`` raises ValueError on a relative
path, which is what broke run 35455946035 after PR #14. These tests pin
that the report resolves before taking a file URI, without requiring
Playwright or its browsers (screenshots are already best-effort).

Revision identity is injected as a dict so unit tests do not need a real
git checkout or GitHub Actions env (same idea as flutter_navigation_basic
overriding BuildMetadata.load in widget tests).
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_FAKE_REVISION = {
    "version": "0.1.0",
    "sha": "abcdef1234567890abcdef1234567890abcdef12",
    "shortSha": "abcdef12",
    "ref": "main",
    "committedAt": "2026-09-19T16:50:27Z",
    "subject": "Fix GitHub Pages report crash",
    "commitUrl": "https://github.com/myon-bioinformatics/markdown/commit/abcdef1234567890abcdef1234567890abcdef12",
    "dirty": False,
}


def _load_report_module():
    path = ROOT / "scripts" / "real_world_pages_report.py"
    spec = importlib.util.spec_from_file_location("real_world_pages_report", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _stub_screenshot(report, monkeypatch) -> list[str]:
    seen_uris: list[str] = []

    def fake_screenshot(file_uri: str, png_path: Path) -> bool:
        seen_uris.append(file_uri)
        parsed = urlparse(file_uri)
        assert parsed.scheme == "file", file_uri
        local = Path(unquote(parsed.path))
        assert local.is_absolute(), file_uri
        return False

    monkeypatch.setattr(report, "_screenshot", fake_screenshot)
    return seen_uris


def test_build_report_with_relative_out_does_not_raise_on_as_uri(tmp_path, monkeypatch) -> None:
    report = _load_report_module()
    monkeypatch.chdir(tmp_path)
    seen_uris = _stub_screenshot(report, monkeypatch)

    report.build_report(Path("_site"))

    assert (tmp_path / "_site" / "index.html").is_file()
    assert seen_uris
    assert all(uri.startswith("file://") for uri in seen_uris)


def test_build_report_embeds_injected_revision_and_writes_build_meta(tmp_path, monkeypatch) -> None:
    report = _load_report_module()
    monkeypatch.chdir(tmp_path)
    seen_uris = _stub_screenshot(report, monkeypatch)

    report.build_report(Path("_site"), revision=_FAKE_REVISION)

    index = (tmp_path / "_site" / "index.html").read_text(encoding="utf-8")
    assert "abcdef12" in index
    assert "Version 0.1.0" in index
    assert 'id="build-meta"' in index
    assert _FAKE_REVISION["commitUrl"] in index
    assert _FAKE_REVISION["committedAt"] in index
    assert _FAKE_REVISION["subject"] in index
    assert _FAKE_REVISION["sha"] in index
    assert seen_uris
    assert all(uri.startswith("file://") for uri in seen_uris)

    meta_path = tmp_path / "_site" / "build_meta.json"
    assert meta_path.is_file()
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    assert meta["shortSha"] == "abcdef12"
    assert meta["sha"] == _FAKE_REVISION["sha"]
    assert meta["commitUrl"] == _FAKE_REVISION["commitUrl"]
    assert meta["version"] == "0.1.0"


def test_build_report_omits_version_label_when_absent(tmp_path, monkeypatch) -> None:
    report = _load_report_module()
    monkeypatch.chdir(tmp_path)
    _stub_screenshot(report, monkeypatch)

    revision = {**_FAKE_REVISION, "version": None}
    report.build_report(Path("_site"), revision=revision)

    index = (tmp_path / "_site" / "index.html").read_text(encoding="utf-8")
    assert "abcdef12" in index
    assert "Version " not in index
    assert "Commit abcdef12" in index


def test_collect_revision_prefers_github_actions_env(monkeypatch) -> None:
    report = _load_report_module()

    def fake_git(args: list[str]) -> str | None:
        table = {
            ("rev-parse", "HEAD"): "gitsha0000000000000000000000000000000000",
            ("rev-parse", "--short=8", "HEAD"): "gitsha00",
            ("branch", "--show-current"): "local-branch",
            ("show", "-s", "--format=%cI", "HEAD"): "2026-01-01T00:00:00+00:00",
            ("show", "-s", "--format=%s", "HEAD"): "local subject",
            ("status", "--porcelain"): " M markdown.py",
        }
        return table.get(tuple(args))

    monkeypatch.setattr(report, "_git_output", fake_git)
    meta = report.collect_revision(
        {
            "GITHUB_SHA": "actions1234567890abcdef1234567890abcdef12",
            "GITHUB_REF_NAME": "main",
            "GITHUB_REPOSITORY": "myon-bioinformatics/markdown",
            "GITHUB_SERVER_URL": "https://github.com",
        }
    )
    assert meta["sha"] == "actions1234567890abcdef1234567890abcdef12"
    assert meta["shortSha"] == "actions1"
    assert meta["ref"] == "main"
    assert meta["commitUrl"] == (
        "https://github.com/myon-bioinformatics/markdown/commit/"
        "actions1234567890abcdef1234567890abcdef12"
    )
    assert meta["committedAt"] == "2026-01-01T00:00:00+00:00"
    assert meta["subject"] == "local subject"
    assert meta["dirty"] is True
    assert meta["version"] is None


def test_collect_revision_falls_back_to_git_when_actions_env_absent(monkeypatch) -> None:
    report = _load_report_module()

    def fake_git(args: list[str]) -> str | None:
        table = {
            ("rev-parse", "HEAD"): "deadbeefcafebabe000000000000000000000000",
            ("rev-parse", "--short=8", "HEAD"): "deadbeef",
            ("branch", "--show-current"): "cursor/pages-build-meta",
            ("show", "-s", "--format=%cI", "HEAD"): "2026-09-19T12:00:00+00:00",
            ("show", "-s", "--format=%s", "HEAD"): "Add Pages revision identity",
            ("status", "--porcelain"): "",
        }
        return table.get(tuple(args))

    monkeypatch.setattr(report, "_git_output", fake_git)
    meta = report.collect_revision({})
    assert meta["sha"] == "deadbeefcafebabe000000000000000000000000"
    assert meta["shortSha"] == "deadbeef"
    assert meta["ref"] == "cursor/pages-build-meta"
    assert meta["commitUrl"] is None
    assert meta["dirty"] is False
    assert meta["subject"] == "Add Pages revision identity"


def test_collect_revision_git_unavailable(monkeypatch) -> None:
    report = _load_report_module()
    monkeypatch.setattr(report, "_git_output", lambda args: None)
    meta = report.collect_revision({})
    assert meta["sha"] is None
    assert meta["shortSha"] is None
    assert meta["ref"] is None
    assert meta["committedAt"] is None
    assert meta["subject"] is None
    assert meta["commitUrl"] is None
    assert meta["dirty"] is False
    assert meta["version"] is None


def test_collect_revision_reads_markdown_version_when_present(monkeypatch) -> None:
    report = _load_report_module()
    monkeypatch.setattr(report, "_git_output", lambda args: None)
    monkeypatch.setattr(report.md, "__version__", "9.9.9", raising=False)
    meta = report.collect_revision({})
    assert meta["version"] == "9.9.9"
