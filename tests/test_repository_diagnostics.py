import hashlib
import json
from pathlib import Path

from scripts import repository_diagnostics as diagnostics

ROOT = Path(__file__).resolve().parents[1]


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def test_vendor_provenance_matches_bytes():
    contract_p = json.loads((ROOT / "vendor/repository_metadata_contract.provenance.json").read_text())
    resolver_p = json.loads((ROOT / "vendor/github_public_resolver.provenance.json").read_text())
    inspector_p = json.loads((ROOT / "vendor/git_inspector.provenance.json").read_text())
    assert _git_blob_sha(ROOT / "vendor/repository_metadata_contract.py") == contract_p["blob_sha"]
    assert _git_blob_sha(ROOT / "vendor/github_public_resolver.py") == resolver_p["blob_sha"]
    assert _git_blob_sha(ROOT / "vendor/git_inspector.py") == inspector_p["blob_sha"]
    assert inspector_p["source_repository"] == "myon-bioinformatics/myon-bioinformatics"
    assert inspector_p["source_commit"] == "cffa7017c95634bfb6ed6b269d255d56680a894c"


def test_payload_not_checked_roundtrip(tmp_path, monkeypatch):
    record = diagnostics.CONTRACT.build_repository_record(
        full_name="myon-bioinformatics/markdown",
        sha="a" * 40,
        branch="main",
        timestamp="2026-09-27T20:00:00+09:00",
        subject="test",
        generated_at="2026-09-27T21:00:00+09:00",
        working_tree_bytes=1,
        tooling={"python": "3.12"},
    )
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
        diagnostics.GIT_INSPECTOR,
        "ls_files",
        lambda root: {
            "paths": ["space 日本語.txt", "missing.txt"],
            "truncated": False,
        },
    )
    assert diagnostics._tracked_bytes() == 3


def test_tracked_bytes_rejects_incomplete_inventory(monkeypatch):
    monkeypatch.setattr(
        diagnostics.GIT_INSPECTOR,
        "ls_files",
        lambda root: {"paths": ["partial"], "truncated": True},
    )
    with __import__("pytest").raises(RuntimeError, match="truncated"):
        diagnostics._tracked_bytes()
