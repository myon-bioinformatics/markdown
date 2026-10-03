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




import subprocess
import pytest


@pytest.mark.parametrize('case', json.loads(
    (ROOT / 'tests/fixtures/pages_revision_migration.json').read_text()
), ids=lambda case: case['name'])
def test_revision_before_after_fixture(case, monkeypatch):
    report = _load_report_module()
    expected = case['after']

    def canonical(root, full_name, *, env):
        assert root == report.ROOT
        assert full_name == 'myon-bioinformatics/markdown'
        assert env == case['env']
        if case['name'] == 'unavailable':
            raise FileNotFoundError('git')
        return {'head': {'sha': expected['sha'], 'branch': expected['ref'],
                         'timestamp': expected['committedAt'], 'subject': expected['subject']}}

    def status(root):
        assert root == report.ROOT
        if case['name'] == 'unavailable':
            raise report.GIT_INSPECTOR.GitInspectionError('git unavailable')
        return {'clean': not expected['dirty'], 'truncated': False}

    monkeypatch.setattr(report.GENERATOR, 'record_from_checkout', canonical)
    monkeypatch.setattr(report.GIT_INSPECTOR, 'status', status)
    assert report.collect_revision(case['env']) == expected
    assert set(case['before']) == set(expected)
    if case['name'] in ('clean', 'dirty'):
        assert case['before'] == expected
    rendered = report._revision_html(expected)
    if expected['dirty'] is None:
        assert '(dirty unknown)' in rendered
    elif expected['dirty']:
        assert '(dirty)' in rendered
    else:
        assert '(dirty' not in rendered


def _checkout(tmp_path):
    def git(*args):
        return subprocess.check_output(['git', '-C', str(tmp_path), *args], text=True).strip()
    git('init', '-b', 'main')
    git('config', 'user.name', 'Pages fixture')
    git('config', 'user.email', 'pages@example.invalid')
    (tmp_path / 'tracked.txt').write_text('initial\n')
    git('add', 'tracked.txt')
    git('commit', '-m', 'Pages fixture commit')
    return git


def test_real_checkout_clean_dirty_detached_and_actions(tmp_path, monkeypatch):
    report = _load_report_module()
    git = _checkout(tmp_path)
    monkeypatch.setattr(report, 'ROOT', tmp_path)
    sha = git('rev-parse', 'HEAD')
    clean = report.collect_revision({})
    assert clean['sha'] == sha
    assert clean['shortSha'] == sha[:8]
    assert clean['ref'] == 'main'
    assert clean['subject'] == 'Pages fixture commit'
    assert clean['committedAt'] == git('show', '-s', '--format=%cI', 'HEAD')
    assert clean['dirty'] is False
    # Existing inspector handles filenames, including Unicode and newlines.
    untracked = tmp_path / '未追跡\nfile.txt'
    untracked.write_text('untracked')
    assert report.collect_revision({})['dirty'] is True
    untracked.unlink()
    (tmp_path / 'tracked.txt').write_text('modified\n')
    assert report.collect_revision({})['dirty'] is True
    git('add', 'tracked.txt')
    assert report.collect_revision({})['dirty'] is True
    git('commit', '-m', 'Updated fixture')
    git('checkout', '--detach')
    detached = report.collect_revision({})
    assert detached['ref'] == 'detached'
    assert detached['dirty'] is False
    actions = report.collect_revision({'GITHUB_SHA': 'f'*40,
                                      'GITHUB_REF_NAME': '42/merge',
                                      'GITHUB_HEAD_REF': 'feature/pages'})
    assert actions['sha'] == detached['sha']
    assert actions['ref'] == 'feature/pages'
    assert report.collect_revision({'GITHUB_REF_NAME': '42/merge'})['ref'] == '42/merge'


@pytest.mark.parametrize('failure', ['missing_git', 'not_worktree', 'unborn'])
def test_unmeasurable_checkout(tmp_path, monkeypatch, failure):
    report = _load_report_module()
    monkeypatch.setattr(report, 'ROOT', tmp_path)
    if failure == 'missing_git':
        monkeypatch.setenv('PATH', str(tmp_path))
    elif failure == 'unborn':
        subprocess.run(['git', 'init', str(tmp_path)], check=True, capture_output=True)
    meta = report.collect_revision({'GITHUB_SHA': 'a'*40, 'GITHUB_REF_NAME': 'main'})
    assert all(meta[key] is None for key in
               ('sha', 'shortSha', 'ref', 'committedAt', 'subject', 'commitUrl'))
    # An unborn worktree can have a successfully measured clean status despite
    # its identity being unknown; the two measurements remain independent.
    assert meta['dirty'] is (False if failure == 'unborn' else None)


@pytest.mark.parametrize('failure', ['error', 'truncated'])
def test_status_failure_does_not_erase_identity(tmp_path, monkeypatch, failure):
    report = _load_report_module()
    git = _checkout(tmp_path)
    monkeypatch.setattr(report, 'ROOT', tmp_path)

    def status(root):
        if failure == 'error':
            raise report.GIT_INSPECTOR.GitInspectionError('failed observation')
        return {'clean': False, 'truncated': True, 'records': []}

    monkeypatch.setattr(report.GIT_INSPECTOR, 'status', status)
    meta = report.collect_revision({})
    assert meta['sha'] == git('rev-parse', 'HEAD')
    assert meta['dirty'] is None
    assert '(dirty unknown)' in report._revision_html(meta)


def test_canonical_validation_failure_keeps_dirty_observation(tmp_path, monkeypatch):
    report = _load_report_module()
    _checkout(tmp_path)
    monkeypatch.setattr(report, 'ROOT', tmp_path)
    (tmp_path / 'tracked.txt').write_text('modified')

    def fail(*args, **kwargs):
        raise ValueError('canonical metadata is not valid')

    monkeypatch.setattr(report.GENERATOR, 'record_from_checkout', fail)
    monkeypatch.setattr(report.md, '__version__', '9.9.9', raising=False)
    meta = report.collect_revision({'GITHUB_SHA': 'a'*40})
    assert meta['sha'] is None
    assert meta['dirty'] is True
    assert meta['version'] == '9.9.9'
