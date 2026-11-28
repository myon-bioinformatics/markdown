"""🧰 Tooling: frontend dependency slices, installability, the public API, diagnostics, vendor automation wiring, the README doctest, repository metadata, runtime workflow, stdio CLI and the demo apps' logic."""
from __future__ import annotations

import importlib.util
import ast
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest import mock

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
import markdown as md
from scripts import markdown_repository_diagnostics as diagnostics


# ═══ · frontend nano ci ══════════════════════════════════════════════════════════════════════════════════
# Offline contracts for dependency slices and fail-closed frontend evidence.

from scripts import check_frontend_slice as checker


def load_vendored(name, relpath):
    """Load a vendored file by path under a repo-unique name (cli_args README: Loading a vendored copy)."""
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, Path(__file__).resolve().parents[1] / relpath)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name]


run_cli = load_vendored("markdown_cli_args", "vendor/cli_args.py").run_cli


class FrontendNanoTests(unittest.TestCase):
    def test_groups_preserve_existing_frontend_roots(self):
        project = tomllib.loads((ROOT / 'pyproject.toml').read_text())
        groups = project['dependency-groups']
        self.assertEqual(groups['frontend-gradio'], ['gradio>=6.30.0'])
        self.assertEqual(groups['frontend-streamlit'], ['streamlit>=1.66.0'])
        self.assertEqual(groups['frontend-browser'], ['playwright>=1.64.0'])
        self.assertEqual(groups['frontend'], [
            {'include-group': 'frontend-gradio'},
            {'include-group': 'frontend-streamlit'},
            {'include-group': 'frontend-browser'},
        ])
        lock = tomllib.loads((ROOT / 'uv.lock').read_text())
        package = next(p for p in lock['package'] if p['name'] == 'md-market')
        self.assertEqual(package['dev-dependencies']['frontend'], [
            {'name': 'gradio'}, {'name': 'playwright'}, {'name': 'streamlit'}])
        for name in ('gradio', 'streamlit', 'browser'):
            root = 'playwright' if name == 'browser' else name
            self.assertEqual(package['dev-dependencies'][f'frontend-{name}'], [{'name': root}])

    def test_expected_identities_cover_every_existing_slice_test(self):
        actual = set()
        for frontend in checker.EXPECTED:
            path = ROOT / f'tests/frontend/test_{frontend}.py'
            tree = ast.parse(path.read_text())
            actual.update((f'tests.frontend.{path.stem}', node.name)
                          for node in tree.body
                          if isinstance(node, ast.FunctionDef) and node.name.startswith('test_'))
        expected = set.union(*checker.EXPECTED.values())
        self.assertEqual(actual, expected)
        self.assertEqual(len(expected), 7)

    def test_workflow_uses_one_combined_environment_without_browser_execution(self):
        workflow = (ROOT / '.github/workflows/ci.yml').read_text()
        block = workflow.split('  frontend-mock-pytest-latest:', 1)[1].split('  failure-identity:', 1)[0]
        self.assertNotIn('matrix:', block)
        self.assertIn('--group frontend ', block)
        self.assertIn('uv run --no-sync pytest -q', block)
        self.assertIn('scripts/check_frontend_slice.py all', block)
        self.assertIn('if-no-files-found: error', block)
        self.assertNotIn('playwright install', block)
        self.assertIn('for framework in ("gradio", "streamlit", "playwright"):', block)
        for frontend in checker.EXPECTED:
            self.assertIn(f'tests/frontend/test_{frontend}.py', block)
        self.assertNotIn('workflow_dispatch:', workflow)
        self.assertNotIn('frontend-smoke:', workflow)

    def test_complete_reports_and_rejection_probes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'junit.xml'
            choices = dict(checker.EXPECTED, all=set.union(*checker.EXPECTED.values()))
            for frontend, identities in choices.items():
                for mutation in ('good', 'missing', 'duplicate', 'renamed', 'skipped', 'failure', 'error'):
                    with self.subTest(frontend=frontend, mutation=mutation):
                        root = ET.Element('testsuites')
                        suite = ET.SubElement(root, 'testsuite')
                        for classname, name in sorted(identities):
                            ET.SubElement(suite, 'testcase', classname=classname, name=name)
                        case = suite[0]
                        if mutation == 'missing':
                            suite.remove(case)
                        elif mutation == 'duplicate':
                            ET.SubElement(suite, 'testcase', **case.attrib)
                        elif mutation == 'renamed':
                            case.set('name', 'unexpected')
                        elif mutation in ('skipped', 'failure', 'error'):
                            ET.SubElement(case, mutation)
                        ET.ElementTree(root).write(path)
                        if mutation == 'good':
                            checker.check(frontend, path)
                        else:
                            with self.assertRaises(ValueError):
                                checker.check(frontend, path)


# ═══ · installable project ═══════════════════════════════════════════════════════════════════════════════
# The repository root must stay installable by ``uv pip install`` of the git URL.
#
# The parent vendor driver treats a missing build backend, ``tool.uv.package = false``,
# or any third-party runtime dependency as a skip. ``markdown.py`` itself stays a
# stdlib-only file so a standalone copy still imports under ``python -S``.

def test_root_project_is_uv_installable_without_runtime_deps():
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = data["project"]
    assert project["name"] == "md-market"
    assert project["requires-python"] == ">=3.11"
    assert project["dependencies"] == []
    assert data["build-system"]["build-backend"] == "hatchling.build"
    requires = data["build-system"]["requires"]
    assert requires and all(">=" in item and "==" not in item for item in requires)
    uv_tool = data.get("tool", {}).get("uv", {})
    assert uv_tool.get("package") is not False
    wheel = data["tool"]["hatch"]["build"]["targets"]["wheel"]
    assert wheel["only-include"] == ["markdown.py"]


def test_standalone_copy_imports_under_python_s(tmp_path):
    import os
    import subprocess
    import sys

    destination = tmp_path / "markdown.py"
    destination.write_bytes((ROOT / "markdown.py").read_bytes())
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    completed = subprocess.run(
        [sys.executable, "-S", "-c", "import markdown; print(markdown.make_link('A', 'https://example.com'))"],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "[A](https://example.com)"


# ═══ · markdown api ══════════════════════════════════════════════════════════════════════════════════════


FIXTURES = ROOT / "fixtures"


def test_save_and_read_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "note.md"
    message = md.save_markdown("# Hi\n\nbody\n", str(path))
    assert message.startswith("Saved successfully:")
    result = md.read_markdown(str(path), count_hashtags=True)
    assert result["success"] is True
    assert result["content"].startswith("# Hi")
    assert result["hashtag_count"] == 1


def test_read_missing_file(tmp_path: Path) -> None:
    result = md.read_markdown(str(tmp_path / "missing.md"))
    assert result["success"] is False
    assert "Error reading file" in result["content"]


def test_extract_and_split_sections() -> None:
    content = "# A\n\npara\n\n## B\n\nmore\n"
    sections = md.extract_sections(content)
    assert sections == [
        {"level": 1, "title": "A"},
        {"level": 2, "title": "B"},
    ]
    parts = md.split_sections(content)
    assert parts[0]["level"] == 1
    assert "para" in parts[0]["content"]
    assert parts[1]["title"] == "B"


def test_split_slides_at_thematic_breaks() -> None:
    deck = (
        "---\ntheme: plain\nsize: 16:9\n---\n\n"            # front matter: the deck's settings, not a page
        "# One\n\nfirst body\n\n---\n\n"
        "## Two\n\n```yaml\n---\nkey: value\n```\n\n***\n\n"   # a break inside a fence is text
        "no heading here\n\n___\n\n___\n\n"                # two breaks in a row: an empty page between
        "Setext title\n---\n\ntext under it\n\n---\n"      # an underline is not a break; a trailing break adds no page
    )
    slides = md.split_slides(deck)
    assert [(s["level"], s["title"]) for s in slides] == [(1, "One"), (2, "Two"), (0, ""), (0, ""), (0, "")]
    assert slides[0] == {"level": 1, "title": "One", "body": "\nfirst body".strip("\n"), "content": "# One\n\nfirst body"}
    assert slides[1]["body"] == "```yaml\n---\nkey: value\n```"
    assert slides[2]["content"] == slides[2]["body"] == "no heading here"
    assert slides[3]["content"] == ""
    assert slides[4]["content"] == "Setext title\n---\n\ntext under it"
    assert md.split_slides("") == [] and md.split_slides("---\n\n---\n") == []
    assert [s["content"] for s in md.split_slides("---\n\n# A\n\n---\n\nB")] == ["# A", "B"]     # no closing line: not front matter
    assert [s["content"] for s in md.split_slides("a\n\n- - -\n\nb\r\n\r\n* * *\r\n\r\nc")] == ["a", "b", "c"]
    assert [s["title"] for s in md.split_slides("---\ntitle: x\n...\n# Only")] == ["Only"]
    whole = "# A\n\ntext\n"
    assert md.split_slides(whole) == [{"level": 1, "title": "A", "body": "text", "content": "# A\n\ntext"}]


def test_builders_and_focused_html_markdown() -> None:
    assert md.make_link("Docs", "https://example.com") == "[Docs](https://example.com)"
    assert md.make_image("Alt", "a.png", "t") == '![Alt](a.png "t")'

    html_img = '<img src="a.png" alt="Alt" title="t" />'
    assert md.html_image_to_markdown(html_img) == '![Alt](a.png "t")'
    assert 'src="a.png"' in md.markdown_image_to_html('![Alt](a.png "t")')

    html_a = '<a href="https://example.com" title="Ex">Docs</a>'
    assert md.html_link_to_markdown(html_a) == '[Docs](https://example.com "Ex")'
    assert 'href="https://example.com"' in md.markdown_link_to_html(
        '[Docs](https://example.com "Ex")'
    )


def test_html_markdown_subset_roundtrip_ish() -> None:
    html = "<h1>Title</h1><p>Hello <strong>world</strong> and <a href=\"u\">link</a>.</p>"
    converted = md.html_to_markdown(html)
    assert converted.startswith("# Title")
    assert "**world**" in converted
    assert "[link](u)" in converted

    markdown = "# Title\n\nHello **world** and [link](https://ex.com).\n\n```py\nprint(1)\n```\n"
    html_out = md.markdown_to_html(markdown)
    assert "<h1>Title</h1>" in html_out
    assert "<strong>world</strong>" in html_out
    assert "<pre><code" in html_out


def test_is_probably_url() -> None:
    assert md.is_probably_url("https://example.com/a")
    assert not md.is_probably_url("logo.png")


def test_inventory_basic() -> None:
    content = (FIXTURES / "vscode_readme_snippet.md").read_text(encoding="utf-8")
    inv = md.inventory(content)
    assert inv["heading_count"] >= 3
    assert inv["image_count"] >= 1
    assert inv["link_count"] >= 2
    assert inv["code_block_count"] >= 1
    assert inv["horizontal_rule_count"] >= 1
    assert "supported" in inv and "unsupported" in inv


def test_markdown_to_web_ui_v1_document() -> None:
    html = md.markdown_to_web_ui_v1(
        "# Body\n\nHello **world**.",
        title='Docs <unsafe>',
        theme="github-like",
    )
    assert '<body data-ui-theme="github-like">' in html
    assert '<main class="ui-page">' in html
    assert '<h1 class="ui-title">Docs &lt;unsafe&gt;</h1>' in html
    assert '<section class="ui-panel">' in html
    assert "<strong>world</strong>" in html
    assert "<style>" not in html


def test_markdown_to_web_ui_v1_rejects_unknown_theme() -> None:
    with pytest.raises(ValueError):
        md.markdown_to_web_ui_v1("x", theme="unknown")


def test_markdown_to_web_ui_v1_empty_content() -> None:
    html = md.markdown_to_web_ui_v1("", theme="modern")
    assert '<body data-ui-theme="modern">' in html
    assert '<main class="ui-page">' in html
    assert '<section class="ui-panel">' in html
    assert '</section>' in html
    assert '<h1 class="ui-title">' not in html


def test_markdown_to_web_ui_v1_theme_is_case_sensitive() -> None:
    with pytest.raises(ValueError):
        md.markdown_to_web_ui_v1("x", theme="Modern")


# ═══ · markdown repository diagnostics ═══════════════════════════════════════════════════════════════════

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
    html = (tmp_path / diagnostics.HTML_NAME).read_text(encoding="utf-8")
    assert '<link rel="icon" type="image/png" href="./favicon.png">' in html
    assert '<link rel="apple-touch-icon" href="./icon.png">' in html
    assert 'src="./icon.png"' in html
    # ♻️ ./icon.png and ./favicon.png come from CaChereCyCle on Pages (guide_brand); no copy is written here
    assert not (tmp_path / "icon.png").exists() and not (tmp_path / "favicon.png").exists()


def test_page_is_the_shared_self_contained_renderer():
    html = diagnostics.page_html()
    assert "<title>myon-bioinformatics/markdown repository diagnostics</title>" in html
    assert "cdn.jsdelivr.net" not in html and '<link rel="stylesheet"' not in html
    assert "/* css/repository-diagnostics.css */" in html and "global.RepositoryDiagnostics = api" in html
    assert 'RepositoryDiagnostics.mount(document, "./repository-diagnostics.json");' in html
    assert "repository-diagnostics.jsonl" in html


def test_page_rejects_a_repository_name_that_is_not_owner_slash_name(monkeypatch):
    import pytest
    monkeypatch.setattr(diagnostics, "REPOSITORY", '<repo & "quoted">')
    with pytest.raises(ValueError):
        diagnostics.page_html()


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


# ═══ · markdown vendor automation ════════════════════════════════════════════════════════════════════════
# Vendor lock CI wiring: pinned vendor_sync check without upstream auto-update.

WORKFLOW = ".github/workflows/ci.yml"
VENDOR_SYNC_PIN = "26c442bc51b8a2837fe2556782b2937f396932af"
GHI_LOAD_COMMAND = (
    'python -S -c "import importlib.util; '
    "s=importlib.util.spec_from_file_location('vendored_ghi','vendor/gh_identity.py'); "
    'm=importlib.util.module_from_spec(s); s.loader.exec_module(m); '
    "assert hasattr(m,'capabilities')\""
)


def _workflow():
    import yaml

    return yaml.load((ROOT / WORKFLOW).read_text(encoding="utf-8"), Loader=yaml.BaseLoader)


def test_ci_verifies_lock_without_promote_or_update():
    ci = _workflow()
    assert {"push", "pull_request"} <= set(ci["on"])
    assert "schedule" not in ci["on"]
    assert "vendor-mode" not in (ROOT / WORKFLOW).read_text(encoding="utf-8")
    jobs = ci["jobs"]
    resolve = jobs["resolve-vendor"]["steps"]
    test = jobs["test"]["steps"]
    assert jobs["resolve-vendor"]["permissions"] == jobs["test"]["permissions"] == {"contents": "read"}
    recreate = next(s for s in resolve if s.get("name") == "Recreate locked vendor files from GitHub")
    assert recreate["shell"] == "bash"
    assert recreate["run"].splitlines() == [
        "python -S .vendor-sync-tools/vendor_sync.py recreate --manifest vendor.lock.json",
    ]
    needs = jobs["test"]["needs"]
    assert "resolve-vendor" in ([needs] if isinstance(needs, str) else needs)
    assert not any(
        command in s.get("run", "")
        for steps in (resolve, test)
        for s in steps
        for command in ("vendor_sync.py update", "vendor_sync.py promote")
    )
    assert not any(s.get("uses", "").startswith("actions/download-artifact@") for s in test)
    verify = next(i for i, s in enumerate(test) if s.get("name") == "Verify checked-in vendor copies")
    load = next(i for i, s in enumerate(test) if s.get("name") == "Verify enrolled GHI is stdlib-loadable")
    tests = [i for i, s in enumerate(test) if "pytest " in s.get("run", "")]
    assert tests and verify < load < min(tests)
    assert test[load]["run"] == GHI_LOAD_COMMAND
    pins = [
        s["with"]["ref"]
        for steps in (resolve, test)
        for s in steps
        if s.get("with", {}).get("repository") == "myon-bioinformatics/myon-bioinformatics"
    ]
    assert pins == [VENDOR_SYNC_PIN] * 2
    for steps in (resolve, test):
        for step in steps:
            if step.get("uses", "").startswith("actions/checkout@"):
                assert step["with"]["persist-credentials"] == "false"
            assert not any(x in step.get("run", "") for x in ("|| true", "|| :", "set +e", "git push", "git commit", "gh pr"))
            assert "continue-on-error" not in step
    text = (ROOT / WORKFLOW).read_text(encoding="utf-8")
    assert not any(x in text for x in ("secrets.", "VENDOR_UPDATE_TOKEN", "VENDOR_UPDATES_ENABLED", "GH_TOKEN"))


def test_locked_baseline_runs_automatically_without_candidate_snapshot():
    ci = _workflow()
    job = ci["jobs"]["vendor-locked"]
    assert job["permissions"] == {"contents": "read"}
    assert "continue-on-error" not in job
    assert job.get("needs") == ci["jobs"]["resolve-vendor"].get("needs")
    assert job.get("if") == ci["jobs"]["resolve-vendor"].get("if")
    matrix = job.get("strategy", {}).get("matrix", {})
    assert all(len(values) == 1 for values in matrix.values())
    steps = job["steps"]
    assert not any(
        command in s.get("run", "")
        for s in steps
        for command in ("vendor_sync.py update", "vendor_sync.py promote")
    )
    assert not any(s.get("uses", "").startswith("actions/download-artifact@") for s in steps)
    verify = next(i for i, s in enumerate(steps) if s.get("name") == "Verify checked-in vendor copies")
    recreate = next(i for i, s in enumerate(steps) if s.get("name") == "Recreate locked vendor files from GitHub")
    load = next(i for i, s in enumerate(steps) if s.get("name") == "Verify enrolled GHI is stdlib-loadable")
    tests = [i for i, s in enumerate(steps) if "pytest " in s.get("run", "")]
    assert tests and verify < recreate < load < min(tests)
    assert steps[load]["run"] == GHI_LOAD_COMMAND
    original = next(s for s in ci["jobs"]["resolve-vendor"]["steps"] if s.get("name") == "Recreate locked vendor files from GitHub")
    assert steps[recreate] == original
    tool = next(s for s in steps if s.get("name") == "Fetch pinned shared vendor tool")
    assert tool["with"]["ref"] == VENDOR_SYNC_PIN
    for step in steps:
        assert "continue-on-error" not in step
        if step.get("uses", "").startswith("actions/checkout@"):
            assert step["with"]["persist-credentials"] == "false"
        if step.get("uses", "").startswith("actions/upload-artifact@"):
            assert step["with"]["name"].startswith("locked-")
            if step["with"]["name"].startswith(("locked-junit-", "locked-controlled-")):
                assert step["if"] == "always()"
            assert step["with"]["if-no-files-found"] == "error"


# ═══ · readme doctest ════════════════════════════════════════════════════════════════════════════════════

def test_run_markdown_doctest_uses_only_python_fences_and_keeps_line_numbers():
    document = """# Example

```text
>>> 1 + 1
3
```

```pycon
>>> 1 + 1
2
```
"""

    source = md._markdown_doctest_source(document)

    assert source.count("\n") == document.count("\n")
    assert "```" not in source
    assert md.run_markdown_doctest(document).failed == 0


def test_run_markdown_doctest_returns_failure_count_without_a_cli():
    document = """# Example

```python
>>> value = 2
>>> value * 3
6
```
"""

    result = md.run_markdown_doctest(document, name="README.md")

    assert result.attempted == 2
    assert result.failed == 0


def test_run_markdown_doctest_reports_failures_without_writing_stdout(capsys):
    document = """```python
>>> 1 + 1
3
```
"""

    result = md.run_markdown_doctest(document)

    assert result == (1, 1)
    assert capsys.readouterr().out == ""


def test_run_markdown_doctest_handles_crlf_line_endings():
    """A correct example must not fail just because the source file uses
    CRLF -- doctest.DocTestParser splits on "\\n", so a stray "\\r" left on
    each Python-fence line would attach to the example/want text."""
    document = "# X\r\n\r\n```python\r\n>>> 1 + 1\r\n2\r\n```\r\n"

    result = md.run_markdown_doctest(document)

    assert result.attempted == 1
    assert result.failed == 0


# ═══ · repository metadata producer ══════════════════════════════════════════════════════════════════════

def _v1_record(**kwargs):
    sha = kwargs["sha"]
    return diagnostics.GH_IDENTITY.validate_repository_metadata_v1({
        "schema_version": "1.0",
        "repository": {"full_name": kwargs["full_name"]},
        "head": {
            "sha": sha,
            "short_sha": sha[:8],
            "branch": kwargs["branch"],
            "timestamp": kwargs["timestamp"],
            "subject": kwargs["subject"],
        },
        "measurements": {
            "github_reported_size_bytes": kwargs.get("github_reported_size_bytes"),
            "working_tree_bytes": kwargs.get("working_tree_bytes"),
            "release_artifact_bytes": kwargs.get("release_artifact_bytes"),
        },
        "tooling": dict(kwargs.get("tooling") or {}),
        "generated_at": kwargs["generated_at"],
    })


class RepositoryMetadataProducerTests(unittest.TestCase):
    def test_generator_delegates_to_vendored_gh_identity_without_sys_path_mutation(self):
        self.assertEqual(Path(diagnostics.GH_IDENTITY.__file__).resolve(),
                         (ROOT / "vendor/gh_identity.py").resolve())
        self.assertNotIn(str(ROOT / "vendor"), sys.path)

    def test_checkout_identity_equivalence_refs_and_detached_head(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "checkout"
            root.mkdir()

            def git(*args, env=None):
                return subprocess.check_output(["git", *args], cwd=root, env=env, text=True).strip()

            git("init", "-q")
            git("config", "user.name", "Metadata test")
            git("config", "user.email", "metadata@example.invalid")
            (root / "README.md").write_text("synthetic checkout\n", encoding="utf-8")
            git("add", "README.md")
            env = dict(
                os.environ,
                GIT_AUTHOR_DATE="2026-09-29T01:02:03+00:00",
                GIT_COMMITTER_DATE="2026-09-29T01:02:03+00:00",
            )
            git("commit", "-qm", "feat: synthetic 日本語", env=env)
            git("branch", "-M", "work")
            head = git("rev-parse", "HEAD")
            now = "2026-09-29T12:34:56Z"
            scenarios = [
                ({}, "work"),
                ({"GITHUB_REF_NAME": "99/merge"}, "99/merge"),
                ({
                    "GITHUB_HEAD_REF": "feature/example",
                    "GITHUB_REF_NAME": "99/merge",
                    "GITHUB_SHA": "d" * 40,
                    "REPOSITORY_DIAGNOSTICS_SHA": "c" * 40,
                }, "feature/example"),
            ]
            for context, branch in scenarios:
                with mock.patch.object(diagnostics, "ROOT", root):
                    record = diagnostics.build_record(context, generated_at=now)
                expected = _v1_record(
                    full_name=diagnostics.REPOSITORY,
                    sha=head,
                    branch=branch,
                    timestamp=git("show", "-s", "--format=%cI", "HEAD"),
                    subject="feat: synthetic 日本語",
                    generated_at=now,
                    working_tree_bytes=len((root / "README.md").read_bytes()),
                    tooling={"python": platform.python_version()},
                )
                self.assertEqual(record, expected)
                self.assertEqual(json.loads(diagnostics._metadata_jsonl(record)), expected)
            git("checkout", "--detach", "-q")
            with mock.patch.object(diagnostics, "ROOT", root):
                detached = diagnostics.build_record({}, generated_at=now)
                with self.assertRaises(ValueError):
                    diagnostics.build_record({}, generated_at="invalid timestamp")
            self.assertEqual(detached["head"]["branch"], "detached")
            self.assertEqual(detached["head"]["sha"], head)

            standalone = Path(tmp) / "standalone"
            standalone.mkdir()
            shutil.copyfile(ROOT / "vendor/gh_identity.py", standalone / "gh_identity.py")
            output = Path(tmp) / "output"
            env = os.environ.copy()
            for name in ("PYTHONPATH", "GITHUB_HEAD_REF", "GITHUB_REF_NAME"):
                env.pop(name, None)
            result = run_cli(
                standalone / "gh_identity.py", "repo-metadata", "--format", "v1",
                "--root", str(root), "--repository", diagnostics.REPOSITORY,
                "--output-dir", str(output),
                python_options=("-S",), cwd=standalone, env=env,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            direct = json.loads((output / "repository-metadata.json").read_text())
            self.assertEqual(direct["head"], detached["head"])
            self.assertEqual(json.loads((output / "repository-metadata.jsonl").read_text()), direct)
            self.assertIsNone(direct["measurements"]["working_tree_bytes"])

    def test_payload_preserves_resolver_and_unsupported_ref_behavior(self):
        record = _v1_record(
            full_name=diagnostics.REPOSITORY, sha="b" * 40, branch="feature/example",
            timestamp="2026-09-29T01:02:03Z", subject="test", generated_at="2026-09-29T01:02:03Z",
        )
        evidence = {"status": "not_checked"}
        with mock.patch.object(diagnostics.RESOLVER, "resolve_public_github", return_value=evidence) as resolver:
            payload = diagnostics.build_payload(record, probe=False)
            resolver.assert_called_once_with(diagnostics.REPOSITORY, ref="feature/example", path="README.md", probe=False)
            self.assertIs(payload["metadata"], record)
            self.assertIs(payload["resolver"], evidence)
        with mock.patch.object(diagnostics.RESOLVER, "resolve_public_github", side_effect=ValueError("ref must be a simple Git ref")):
            self.assertEqual(diagnostics.build_payload(record)["resolver"]["reason"], "unsupported_ref")


# ═══ · runtime workflow ══════════════════════════════════════════════════════════════════════════════════
# Keep dependency-free runtime coverage aligned with the supported Python floor.

def test_runtime_floor_runs_on_the_default_runner_without_skipping_behavior():
    workflow = yaml.safe_load((ROOT / '.github/workflows/runtime-compatibility.yml').read_text())
    job = workflow['jobs']['runtime']
    assert job['runs-on'] == 'ubuntu-latest'
    assert job['strategy']['matrix'] == {'python': ['3.11', '3.12', '3.13', '3.14']}
    assert job['strategy']['fail-fast'] is False
    assert 'if' not in job and not job.get('continue-on-error', False)
    behavior = [step for step in job['steps'] if 'run' in step]
    assert len(behavior) == 1
    assert behavior[0]['run'] == 'python -S -m unittest discover -s tests -p test_runtime_compatibility.py -v'
    assert 'if' not in behavior[0] and not behavior[0].get('continue-on-error', False)
    ci = yaml.safe_load((ROOT / '.github/workflows/ci.yml').read_text())
    assert ci['jobs']['test']['strategy']['matrix']['python-version'] == ['3.11', '3.12', '3.13', '3.14']


def test_source_runtime_floor_matches_packaged_runtime_and_documentation():
    project = tomllib.loads((ROOT / 'pyproject.toml').read_text(encoding='utf-8'))
    assert project['project']['requires-python'] == '>=3.11'
    readme = (ROOT / 'README.md').read_text(encoding='utf-8')
    assert 'source runtime requires Python 3.11 or newer' in readme
    assert 'Python 3.9 and 3.10 are no longer supported.' in readme
    discovery = (ROOT / 'docs/unittest-discovery.md').read_text(encoding='utf-8')
    assert 'Run from this repository root with Python 3.11 or newer.' in discovery


# ═══ · stdio cli ═════════════════════════════════════════════════════════════════════════════════════════

class StdioCli(unittest.TestCase):
 def run_cli(self,*args,input=''):
  return run_cli(ROOT/'markdown.py',*args,python_options=('-S',),stdin=input,timeout=10)
 def test_inventory_and_help(self):
  self.assertEqual(self.run_cli('--help').returncode,0)
  self.run_cli().json()
 def test_transform_stdin_and_missing_input(self):
  result=self.run_cli('to-html',input='# Hello\n')
  self.assertEqual(result.returncode,0,result.stderr)
  self.assertIn('<h1',result.stdout)
  self.assertIn('Hello',result.stdout)
  self.assertEqual(self.run_cli('to-html','/path/that/does/not/exist').returncode,2)
 def test_invalid_operation(self):
  result=self.run_cli('invalid')
  self.assertEqual(result.returncode,2)
  self.assertNotIn('Traceback',result.stderr)


# ═══ · chat ui demo logic ════════════════════════════════════════════════════════════════════════════════
# No-browser coverage for chat_ui_demo's rendering logic.
#
# ``render_assistant_turn`` / ``respond`` import neither gradio nor any chat
# framework at module scope — plain Python, testable as a one-liner, matching
# ``demos/gradio_app.py``'s ``analyze()``.

for path in (str(ROOT), str(ROOT / "demos")):
    if path not in sys.path:
        sys.path.insert(0, path)

import chat_ui_demo as chat_ui  # noqa: E402


def test_table_reply_renders_a_real_markdown_table() -> None:
    reply = chat_ui.render_assistant_turn("Show me a results table")
    assert "| metric | value |" in reply
    assert "| loss | 0.041 |" in reply
    html = md.markdown_to_html(reply)
    assert "<table>" in html
    assert "<th>metric</th>" in html
    assert "<td>loss</td>" in html


def test_code_reply_renders_a_fenced_block() -> None:
    reply = chat_ui.render_assistant_turn("show me some code")
    assert "```python" in reply
    assert "md.bold" in reply


def test_list_reply_renders_bullets() -> None:
    reply = chat_ui.render_assistant_turn("give me a todo list")
    assert "- review the PR" in reply
    assert "- ship it" in reply


def test_default_reply_uses_bold_and_italic() -> None:
    reply = chat_ui.render_assistant_turn("hello there")
    assert "**Got it.**" in reply
    assert "*Ask for a table, code, or list to see more.*" in reply


def test_respond_appends_user_then_assistant_turn() -> None:
    cleared, history = chat_ui.respond("table please", [])
    assert cleared == ""
    assert history[0] == {"role": "user", "content": "table please"}
    assert history[1]["role"] == "assistant"
    assert "| metric | value |" in history[1]["content"]


def test_respond_preserves_prior_history() -> None:
    _, first = chat_ui.respond("hello", [])
    _, second = chat_ui.respond("now a list please", first)
    assert len(second) == 4
    assert second[:2] == first


def test_sample_conversation_is_well_formed() -> None:
    assert chat_ui.SAMPLE_CONVERSATION[0]["role"] == "user"
    assert chat_ui.SAMPLE_CONVERSATION[1]["role"] == "assistant"
    assert "| metric | value |" in chat_ui.SAMPLE_CONVERSATION[1]["content"]


# ═══ · demo logic ════════════════════════════════════════════════════════════════════════════════════════
# No-browser, no-click coverage for the demo apps' actual logic.
#
# ``demos/gradio_app.py`` and ``demos/streamlit_app.py`` each keep their real
# work in a plain function (``analyze`` / ``build_view``) that imports neither
# ``gradio`` nor ``streamlit`` at module scope. That means the behavior behind
# each UI is a normal Python library call — testable (and runnable as a
# one-liner) without installing a frontend framework, launching a server, or
# driving a browser.

import gradio_app  # noqa: E402
import streamlit_app  # noqa: E402


def test_gradio_analyze_is_a_plain_function_call() -> None:
    headings, links, images, summary = gradio_app.analyze(
        "# Title\n\n[docs](https://example.com)\n\n![alt text](img.png)\n"
    )
    assert headings == "# Title"
    assert links == "- docs: https://example.com"
    assert images == "- alt text: img.png"
    payload = json.loads(summary)
    assert payload["heading_count"] == 1
    assert payload["link_count"] == 1
    assert payload["image_count"] == 1
    assert payload["urls"] == ["https://example.com", "img.png"]


def test_gradio_analyze_empty_input_shows_placeholders() -> None:
    headings, links, images, summary = gradio_app.analyze("")
    assert headings == "(none)"
    assert links == "(none)"
    assert images == "(none)"
    assert json.loads(summary)["heading_count"] == 0


def test_gradio_analyze_reads_uploaded_file(tmp_path: Path) -> None:
    md_file = tmp_path / "note.md"
    md_file.write_text("# From file\n", encoding="utf-8")
    headings, _, _, _ = gradio_app.analyze("ignored when a file is uploaded", str(md_file))
    assert headings == "# From file"


def test_streamlit_build_view_has_no_streamlit_import() -> None:
    # Checking sys.modules would be order-dependent in a full pytest run (other
    # test files legitimately import the real streamlit); what actually matters
    # is that streamlit_app's own module namespace never binds it, since
    # `import streamlit as st` in build_view()'s caller (main()) is local to
    # that function, not module scope.
    assert "streamlit" not in vars(streamlit_app)


def test_streamlit_build_view_counts_and_preview() -> None:
    view = streamlit_app.build_view("# Only Heading\n\nplain text, no links or images.\n")
    assert view["heading_count"] == 1
    assert view["link_count"] == 0
    assert view["image_count"] == 0
    assert "<h1>Only Heading</h1>" in view["html_preview"]


def test_streamlit_build_view_matches_default_fixture() -> None:
    content = streamlit_app.DEFAULT_FIXTURE.read_text(encoding="utf-8")
    view = streamlit_app.build_view(content)
    assert view["heading_count"] > 0
    assert view["link_count"] > 0


if __name__ == "__main__":
    unittest.main()
