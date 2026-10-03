"""Real Markdown producer failures through the pinned shared JUnit importer."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

import xprobe


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("junit", [False, True])
def test_real_child_failure_evidence(tmp_path, junit):
    """Domain integration; generic classification/receipt coverage lives in xprobe."""
    (tmp_path / "test_markdown_producer.py").write_text('''import sys
import pytest
import markdown as md

# Dummy privacy sentinels only; no real credentials or user data.
@pytest.mark.parametrize("expected", ["SECRET_PARAM_ONE", "SECRET_PARAM_TWO"])
def test_bold_wrong_expectation(expected):
    print("SECRET_STDOUT")
    print("SECRET_STDERR", file=sys.stderr)
    assert md.bold("text") == expected, "SECRET_MESSAGE"

@pytest.fixture
def wrong_setup():
    assert md.heading("Title") == "SECRET_SETUP"

def test_setup(wrong_setup): pass

def test_pass():
    assert md.bold("text") == "**text**"

@pytest.mark.skip(reason="SECRET_SKIP")
def test_skip(): pass
''', encoding="utf-8")
    env = dict(os.environ, PYTHONPATH=str(ROOT), PYTEST_DISABLE_PLUGIN_AUTOLOAD="1")
    env.pop("PYTEST_ADDOPTS", None)
    command = [sys.executable, "-m", "pytest", "-q"]
    if junit:
        command += ["--junitxml=junit.xml", "-o", "junit_logging=all"]
    result = subprocess.run(command, cwd=tmp_path, env=env, capture_output=True,
                            text=True, timeout=30)
    directory = None
    destination = os.environ.get("MARKDOWN_FAILURE_EVIDENCE") if junit else None
    if destination:
        directory = Path(destination)
        directory.mkdir(parents=True)  # Reject reuse rather than mix old evidence.
        (directory / "child-exit.json").write_text(
            json.dumps({"returncode": result.returncode}) + "\n", encoding="utf-8")
        if (tmp_path / "junit.xml").exists():
            shutil.copyfile(tmp_path / "junit.xml", directory / "junit.xml")
    if junit:
        xml = (tmp_path / "junit.xml").read_text(encoding="utf-8")
        report = xprobe.cases_from_junit(
            xml, repository="myon-bioinformatics/markdown",
            commit_sha=None, report_id="controlled-child")
        compact = xprobe.corpus_to_json(report["cases"], jsonl=True)
        if directory is not None:
            (directory / "failures.jsonl").write_text(compact, encoding="utf-8")
        assert report["truncated"] is False
        assert sorted((r["value"]["test"], r["value"]["kind"]) for r in report["cases"]) == [
            ("test_bold_wrong_expectation", "failure"),
            ("test_bold_wrong_expectation", "failure"),
            ("test_setup", "error")]
        assert all(r["context"]["commit_sha"] is None for r in report["cases"])
        assert all(token in xml for token in (
            "SECRET_PARAM_ONE", "SECRET_PARAM_TWO", "SECRET_MESSAGE",
            "SECRET_SETUP", "SECRET_STDOUT", "SECRET_STDERR"))
        assert "SECRET_" not in compact
        assert "Traceback" not in compact
    assert result.returncode == 1
    assert "2 failed, 1 passed, 1 skipped, 1 error" in result.stdout
