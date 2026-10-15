"""Vendor lock CI wiring: pinned vendor_sync check without upstream auto-update."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ".github/workflows/ci.yml"
VENDOR_SYNC_PIN = "ab17b409d82f95abc81116af7ff0d3e7bdc4158c"
GHI_LOAD_COMMAND = (
    'python -S -c "import importlib.util; '
    "s=importlib.util.spec_from_file_location('vendored_ghi','vendor/gh_identity.py'); "
    'm=importlib.util.module_from_spec(s); s.loader.exec_module(m); '
    "assert hasattr(m,'capabilities')\""
)
EXPECTED = {
    ("myon-bioinformatics/gh_identity", "gh_identity.py", "vendor/gh_identity.py"),
    ("myon-bioinformatics/gh_identity", "LICENSE", "vendor/gh_identity-LICENSE"),
    ("myon-bioinformatics/myon-bioinformatics", "LICENSE", "vendor/myon-bioinformatics-LICENSE"),
    ("myon-bioinformatics/Ironmate", "LICENSE", "vendor/Ironmate-LICENSE"),
    ("myon-bioinformatics/mcp-toolcall-lab", "LICENSE", "vendor/mcp-toolcall-lab-LICENSE"),
    (
        "myon-bioinformatics/mcp-toolcall-lab",
        "src/mcp_toolcall_lab/github_public_resolver.py",
        "vendor/github_public_resolver.py",
    ),
}


def _workflow():
    import yaml

    return yaml.load((ROOT / WORKFLOW).read_text(encoding="utf-8"), Loader=yaml.BaseLoader)


def test_vendor_lock_has_explicit_sources():
    lock = json.loads((ROOT / "vendor.lock.json").read_text(encoding="utf-8"))
    assert {(e["repository"], e["source"], e["destination"]) for e in lock["files"]} == EXPECTED


def test_ci_verifies_lock_without_promote_or_update():
    ci = _workflow()
    assert {"push", "pull_request"} <= set(ci["on"])
    assert "schedule" not in ci["on"]
    assert "vendor-mode" not in (ROOT / WORKFLOW).read_text(encoding="utf-8")
    jobs = ci["jobs"]
    resolve = jobs["resolve-vendor"]["steps"]
    test = jobs["pytest"]["steps"]
    assert jobs["resolve-vendor"]["permissions"] == jobs["pytest"]["permissions"] == {"contents": "read"}
    recreate = next(s for s in resolve if s.get("name") == "Recreate locked vendor files from GitHub")
    assert recreate["shell"] == "bash"
    assert recreate["run"].splitlines() == [
        "python -S - <<'PY'",
        "import json",
        "from pathlib import Path",
        "for entry in json.loads(Path('vendor.lock.json').read_text(encoding='utf-8'))['files']:",
        "    Path(entry['destination']).unlink()",
        "PY",
        "python -S .vendor-sync-tools/vendor_sync.py materialize --manifest vendor.lock.json",
        "python -S .vendor-sync-tools/vendor_sync.py check --manifest vendor.lock.json",
    ]
    needs = jobs["pytest"]["needs"]
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
    job = ci["jobs"]["test-locked"]
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
