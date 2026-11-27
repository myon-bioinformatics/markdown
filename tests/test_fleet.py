"""🚢 Fleet contracts through the parent's shared checks (vendor/fleet_check.py): vendor lock bytes and sources,
parent workflow pins, SHA-pinned actions, CI Python setup order and the benchmark -O guard."""
import json, re, unittest

import pytest

from vendor import fleet_check as fleet

ROOT = fleet.repo_root(__file__)
PARENT_WORKFLOW_PIN = "27c46411c0a07d9b4d0f1ad5751ed1bb9e869b5c"
VENDOR_TOOL_PIN = "26c442bc51b8a2837fe2556782b2937f396932af"
ACCEPTED = {"vendor/fleet_check.py": "20de01921e50e9339aa9271b0547a5be7649b3b3"}
# Runtime/diagnostics tools, the fleet checker, and their recorded licenses.
# The retired Ironmate tool's retained license is explicit provenance policy.
REQUIRED_BINDINGS = {
    "vendor/gh_identity.py": ("myon-bioinformatics/gh_identity", "gh_identity.py"),
    "vendor/gh_identity-LICENSE": ("myon-bioinformatics/gh_identity", "LICENSE"),
    "vendor/myon-bioinformatics-LICENSE": (fleet.PARENT, "LICENSE"),
    "vendor/Ironmate-LICENSE": ("myon-bioinformatics/Ironmate", "LICENSE"),
    "vendor/mcp-toolcall-lab-LICENSE": ("myon-bioinformatics/mcp-toolcall-lab", "LICENSE"),
    "vendor/github_public_resolver.py": ("myon-bioinformatics/mcp-toolcall-lab", "src/mcp_toolcall_lab/github_public_resolver.py"),
    "vendor/njs_launch.py": (fleet.PARENT, "njs_launch.py"),
    "vendor/fleet_check.py": (fleet.PARENT, "fleet_check.py"),
}


# ═══ · vendor lock ═══════════════════════════════════════════════════════════════════════════════════════
# The shared checker validates every row's pinned ref and bytes. This
# consumer separately requires its named source and license bindings.

def _check_vendor_contract(root):
    raw_rows = json.loads((root / "vendor.lock.json").read_text(encoding="utf-8"))["files"]
    assert len({row["destination"].casefold() for row in raw_rows}) == len(raw_rows), "duplicate vendor lock destination"
    rows = fleet.check_lock(root)
    for where, origin in REQUIRED_BINDINGS.items():
        assert where in rows, f"missing required vendor binding: {where}"
        assert (rows[where]["repository"], rows[where]["source"]) == origin, f"wrong vendor binding: {where}"
    for where, commit in ACCEPTED.items():
        assert rows[where]["commit"] == commit, f"wrong vendor commit: {where}"


def test_vendor_lock_matches_checked_in_bytes_and_sources():
    _check_vendor_contract(ROOT)


@pytest.mark.parametrize(("change", "error"), [
    ("extra", None),
    ("missing", "missing required vendor binding"),
    ("repointed", "wrong vendor binding"),
    ("duplicate", "duplicate vendor lock destination"),
    ("casefold-duplicate", "duplicate vendor lock destination"),
    ("drift", "vendor/extra-LICENSE"),
])
def test_vendor_bindings_are_required_without_freezing_the_inventory(tmp_path, change, error):
    data = json.loads((ROOT / "vendor.lock.json").read_text(encoding="utf-8"))
    rows = data["files"]
    license_path = "vendor/mcp-toolcall-lab-LICENSE"
    original = next(row for row in rows if row["destination"] == license_path)
    if change == "missing":
        rows.remove(original)
    elif change == "repointed":
        original["source"] = "NOTICE"
    elif change in ("duplicate", "casefold-duplicate"):
        duplicate = original.copy()
        if change == "casefold-duplicate":
            duplicate["destination"] = "vendor/MCP-TOOLCALL-LAB-license"
        rows.append(duplicate)
    elif change in ("extra", "drift"):
        # A second valid destination from an already named repository used to fail.
        rows.append(dict(original, destination="vendor/extra-LICENSE"))
    for row in rows:
        path = row["destination"]
        source = license_path if path in ("vendor/extra-LICENSE", "vendor/MCP-TOOLCALL-LAB-license") else path
        body = (ROOT / source).read_bytes()
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body + b"drift" if change == "drift" and path == "vendor/extra-LICENSE" else body)
    (tmp_path / "vendor.lock.json").write_text(json.dumps(data), encoding="utf-8")
    if error is None:
        _check_vendor_contract(tmp_path)
    else:
        with pytest.raises(AssertionError, match=error):
            _check_vendor_contract(tmp_path)


# ═══ · parent workflow pins ══════════════════════════════════════════════════════════════════════════════
# Local rollout contract; adopted vendor locks are deliberately independent.

def test_parent_workflow_references_use_reviewed_rollout_commit():
    pins = fleet.parent_refs(ROOT, skip=(".vendor-sync-tools",))
    vendor_tool_pins = fleet.parent_refs(ROOT, only=(".vendor-sync-tools",))
    assert pins, "shared parent references must remain observable"
    assert set(pins) == {PARENT_WORKFLOW_PIN}, pins
    assert vendor_tool_pins and set(vendor_tool_pins) == {VENDOR_TOOL_PIN}, vendor_tool_pins


def test_every_action_is_pinned_by_full_sha_with_a_version_comment():
    assert fleet.check_actions(ROOT), "workflow actions must remain observable"


@pytest.mark.parametrize("quote", ["", "'", '"'])
@pytest.mark.parametrize("target", ["uses", "checkout", "vendor"])
@pytest.mark.parametrize("reference", ["reviewed", "main", "9e3da7a"])
def test_reference_detection_preserves_quotes_and_rejects_unreviewed_pins(
    tmp_path, monkeypatch, quote, target, reference
):
    workflows = tmp_path / ".github/workflows"
    workflows.mkdir(parents=True)
    # Keep valid references present so ignoring a quoted bad reference cannot pass.
    (workflows / "baseline.yml").write_text(
        f"  uses: {fleet.PARENT}/.github/workflows/ci.yml@{PARENT_WORKFLOW_PIN}\n"
        f"  repository: {fleet.PARENT}\n"
        f"  ref: {VENDOR_TOOL_PIN}\n"
        "  path: .vendor-sync-tools\n", encoding="utf-8"
    )
    pin = VENDOR_TOOL_PIN if target == "vendor" else PARENT_WORKFLOW_PIN
    ref = pin if reference == "reviewed" else reference
    if target == "uses":
        candidate = f"  uses: {quote}{fleet.PARENT}/.github/workflows/ci.yml@{ref}{quote}\n"
    else:
        path = ".vendor-sync-tools" if target == "vendor" else ".parent-workflows"
        candidate = (
            f"  repository: {quote}{fleet.PARENT}{quote}\n"
            f"  ref: {quote}{ref}{quote}\n"
            f"  path: {quote}{path}{quote}\n"
        )
    (workflows / "candidate.yml").write_text(candidate, encoding="utf-8")
    monkeypatch.setitem(globals(), "ROOT", tmp_path)
    if reference == "reviewed":
        test_parent_workflow_references_use_reviewed_rollout_commit()
    else:
        with pytest.raises(AssertionError):
            test_parent_workflow_references_use_reviewed_rollout_commit()


# ═══ · ci python setup ═══════════════════════════════════════════════════════════════════════════════════
# Stdlib-only contracts for CI Python selection and preserved baselines.

SETUP_UV = "astral-sh/setup-uv@68559e99cc807c1eb7e9238fd43a15bba460eec2"
JOBS = {
    "ci.yml": {
        "resolve-vendor": "3.15",
        "test": "${{ matrix.python-version }}",
        "node-runtime": "3.15",
        "frontend-mock-pytest-latest": "3.15",
        "vendor-locked": "${{ matrix.python-version }}"
    },
    "runtime-compatibility.yml": {
        "runtime": "${{ matrix.python }}"
    }
}
EXPECTED_REPORTS = [
    "junit-py3.11/pytest-3.11.xml",
    "junit-py3.12/pytest-3.12.xml",
    "junit-py3.13/pytest-3.13.xml",
    "junit-py3.14/pytest-3.14.xml",
    "junit-node-ubuntu-latest-26/node-ubuntu-latest-26.xml",
    "junit-node-ubuntu-latest-latest/node-ubuntu-latest-latest.xml",
    "junit-node-windows-latest-26/node-windows-latest-26.xml",
    "junit-node-windows-latest-latest/node-windows-latest-latest.xml",
    "junit-node-macos-latest-26/node-macos-latest-26.xml",
    "junit-node-macos-latest-latest/node-macos-latest-latest.xml"
]


class CiPythonSetupTests(unittest.TestCase):
    def test_contract_inventory_matches_all_python_setup_jobs(self):
        # Fail for stale workflow/job entries as well as newly untested jobs.
        actual = set()
        for path in sorted((ROOT / ".github/workflows").iterdir()):
            if path.suffix not in {".yml", ".yaml"}:
                continue
            text = path.read_text(encoding="utf-8")
            for name in re.findall(r"(?m)^  ([\w-]+):$", text):
                if "uses: astral-sh/setup-uv@" in fleet.workflow_job(ROOT, name, path.name):
                    actual.add((path.name, name))
        expected = {(workflow, name) for workflow, jobs in JOBS.items() for name in jobs}
        self.assertEqual(actual, expected)

    def test_selected_python_is_ready_before_any_python_or_uv_command(self):
        for workflow, jobs in JOBS.items():
            for name, version in jobs.items():
                with self.subTest(workflow=workflow, job=name):
                    fleet.workflow_job(ROOT, name, workflow, setup=SETUP_UV, inputs=(
                        'version: "latest"',
                        f'python-version: "{version}"',
                        "activate-environment: true",
                        "enable-cache: true",
                        "save-cache: ${{ github.event_name == 'push' && github.ref == 'refs/heads/main' }}",  # only main writes
                        "prune-cache: true",
                    ))

    def test_compatibility_matrix_and_required_report_identities_are_preserved(self):
        text = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        self.assertIn("python-version: [\"3.11\", \"3.12\", \"3.13\", \"3.14\"]", text)
        match = re.search(r"expected-reports: '([^']+)'", fleet.workflow_job(ROOT, "failure-identity"))
        self.assertIsNotNone(match)
        self.assertEqual(json.loads(match.group(1)), EXPECTED_REPORTS)

    def test_locked_baseline_and_runtime_floor_are_preserved(self):
        locked = fleet.workflow_job(ROOT, "vendor-locked")
        self.assertRegex(locked, r"python-version:\s*\n\s*- '3\.12'")
        self.assertIn("name: locked-junit-py${{ matrix.python-version }}", locked)
        self.assertIn("uv sync --locked --group dev", locked)
        self.assertEqual(fleet.python_floor(ROOT), ("3.11", ["3.11", "3.12", "3.13", "3.14"]))
        self.assertIn("independent `vendor-locked` job on Python 3.12", (ROOT / "docs/vendor-automation.md").read_text(encoding="utf-8"))


# ═══ · benchmark optimization guard ══════════════════════════════════════════════════════════════════════
# Fault-injection checks do not require a historical git checkout.

class BenchmarkGuardTests(unittest.TestCase):
    def test_scanner_and_toc_mismatches_stop_optimized_execution(self):
        for attribute, replacement, diagnostic in (
            ('_scan_lines', 'lambda lines: []', 'scanner field mismatch'),
            ('table_of_contents', 'lambda content: object()', 'table of contents mismatch'),
        ):
            patch = f"""import markdown
reference = types.ModuleType('guard_reference')
reference._scan_lines = markdown._scan_lines
reference.table_of_contents = markdown.table_of_contents
sys.modules['guard_reference'] = reference
g['subprocess'].check_output = lambda *a, **kw: b'from guard_reference import _scan_lines, table_of_contents'
markdown.{attribute} = {replacement}"""
            with self.subTest(attribute=attribute):
                result = fleet.run_main(ROOT, 'scripts/benchmark_scanned_lines.py', patch, optimized=True, timeout=30)
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertIn(diagnostic, result.stderr)
                self.assertEqual(result.stdout, '')


# 🧰 Scripts: 📝 each one describes itself and ⌨️ one that reads sys.argv declares its arguments (argparse /
# cli_args). Read with ast, never run; the portfolio's script catalog reads the same facts.

class ScriptsDescribeThemselves(unittest.TestCase):
    def test_every_script_has_a_description_and_declared_arguments(self):
        fleet.check_scripts(fleet.repo_root(__file__))

    def test_pull_request_ci_stays_quick(self):
        # ⏱ push limited to branches, superseded PR runs cancelled, every job timed (fleet_check.check_ci)
        fleet.check_ci(fleet.repo_root(__file__))

    def test_root_scripts_import_only_the_standard_library(self):
        root = fleet.repo_root(__file__)
        for path in sorted(root.glob("*.py")):
            if path.name != "conftest.py":
                fleet.check_imports(root, path.name)
