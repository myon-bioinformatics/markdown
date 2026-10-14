import hashlib
import json
from pathlib import Path

from scripts import repository_diagnostics as diagnostics


def _locked(destination):
    root = Path(__file__).resolve().parents[1]
    lock = json.loads((root / "vendor.lock.json").read_text(encoding="utf-8"))
    return next(e for e in lock["files"] if e["destination"] == destination)

ROOT = Path(__file__).resolve().parents[1]


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def test_vendor_provenance_matches_bytes():
    resolver = _locked("vendor/github_public_resolver.py")
    ghi = _locked("vendor/gh_identity.py")
    assert _git_blob_sha(ROOT / "vendor/github_public_resolver.py") == resolver["blob_sha"]
    assert _git_blob_sha(ROOT / "vendor/gh_identity.py") == ghi["blob_sha"]
    assert ghi["repository"] == "myon-bioinformatics/gh_identity"
    assert hashlib.sha256((ROOT / "vendor/gh_identity.py").read_bytes()).hexdigest() == ghi["sha256"]


def test_payload_not_checked_roundtrip(tmp_path, monkeypatch):
    record = diagnostics.GH_IDENTITY.validate_repository_metadata_v1({
        "schema_version": "1.0",
        "repository": {"full_name": "myon-bioinformatics/markdown"},
        "head": {
            "sha": "a" * 40,
            "short_sha": "a" * 8,
            "branch": "main",
            "timestamp": "2026-09-27T20:00:00+09:00",
            "subject": "test",
        },
        "measurements": {
            "github_reported_size_bytes": None,
            "working_tree_bytes": 1,
            "release_artifact_bytes": None,
        },
        "tooling": {"python": "3.12"},
        "generated_at": "2026-09-27T21:00:00+09:00",
    })
    monkeypatch.setattr(diagnostics, "build_record", lambda: record)
    payload = diagnostics.write_outputs(tmp_path, probe=False)
    assert payload["resolver"]["status"] == "not_checked"
    assert json.loads((tmp_path / diagnostics.JSONL_NAME).read_text()) == payload["metadata"]
    assert json.loads((tmp_path / diagnostics.JSON_NAME).read_text())["metadata"] == payload["metadata"]
    assert (tmp_path / diagnostics.HTML_NAME).is_file()


def test_page_uses_pinned_web_ui_renderer():
    html = diagnostics.page_html()
    assert diagnostics.WEB_UI_SHA in html
    assert "RepositoryDiagnostics.render(payload.metadata)" in html
    assert "repository-diagnostics.jsonl" in html
    assert "__REPO__" not in html
    assert "__BASE__" not in html


def test_page_escapes_template_constants(monkeypatch):
    monkeypatch.setattr(diagnostics, "REPOSITORY", '<repo & "quoted">')
    monkeypatch.setattr(diagnostics, "WEB_UI_BASE", 'https://example.test/a?x=1&y="2"')
    html = diagnostics.page_html()
    assert '&lt;repo &amp; &quot;quoted&quot;&gt;' in html
    assert 'https://example.test/a?x=1&amp;y=&quot;2&quot;' in html
    assert '<repo & "quoted">' not in html


def test_tracked_bytes_uses_canonical_inspector_paths(tmp_path, monkeypatch):
    (tmp_path / "space 日本語.txt").write_bytes(b"abc")
    (tmp_path / "missing.txt").write_bytes(b"ignored")
    (tmp_path / "missing.txt").unlink()
    monkeypatch.setattr(diagnostics, "ROOT", tmp_path)
    monkeypatch.setattr(
        diagnostics.GH_IDENTITY,
        "git_ls_files",
        lambda root: {
            "paths": ["space 日本語.txt", "missing.txt"],
            "truncated": False,
        },
    )
    assert diagnostics._tracked_bytes() == 3


def test_tracked_bytes_rejects_incomplete_inventory(monkeypatch):
    monkeypatch.setattr(
        diagnostics.GH_IDENTITY,
        "git_ls_files",
        lambda root: {"paths": ["partial"], "truncated": True},
    )
    with __import__("pytest").raises(RuntimeError, match="truncated"):
        diagnostics._tracked_bytes()
