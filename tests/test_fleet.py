"""🚢 Fleet contracts through the parent's shared checks (vendor/fleet_check.py): vendor lock bytes and sources,
parent workflow pins, CI Python setup order and the benchmark -O guard."""
import json, re, unittest
from collections import Counter

import pytest

from vendor import fleet_check as fleet

ROOT = fleet.repo_root(__file__)
PARENT_WORKFLOW_PIN = "9e3da7ae1846e9604ebc24bb5178f7de094a4e77"
VENDOR_TOOL_PIN = "26c442bc51b8a2837fe2556782b2937f396932af"
ACCEPTED = {"vendor/fleet_check.py": "6c29503cf17eda856766ddfdf4d66a5b0965a8b1"}
LOCKED = {
    ("myon-bioinformatics/gh_identity", "gh_identity.py", "vendor/gh_identity.py"),
    ("myon-bioinformatics/gh_identity", "LICENSE", "vendor/gh_identity-LICENSE"),
    (fleet.PARENT, "LICENSE", "vendor/myon-bioinformatics-LICENSE"),
    ("myon-bioinformatics/Ironmate", "LICENSE", "vendor/Ironmate-LICENSE"),
    ("myon-bioinformatics/mcp-toolcall-lab", "LICENSE", "vendor/mcp-toolcall-lab-LICENSE"),
    ("myon-bioinformatics/mcp-toolcall-lab", "src/mcp_toolcall_lab/github_public_resolver.py", "vendor/github_public_resolver.py"),
    (fleet.PARENT, "njs_launch.py", "vendor/njs_launch.py"),
    (fleet.PARENT, "fleet_check.py", "vendor/fleet_check.py"),
}


# ═══ · vendor lock ═══════════════════════════════════════════════════════════════════════════════════════
# Every locked row (gh_identity, the resolver, the retired Ironmate LICENSE, ...) keeps a full-SHA ref equal
# to its commit and bytes matching both hashes; that is one check_lock call.

def test_vendor_lock_matches_checked_in_bytes():
    fleet.check_lock(ROOT, commits=ACCEPTED)


def test_vendor_lock_has_explicit_sources():
    rows = fleet.check_lock(ROOT)
    assert {(row["repository"], row["source"], where) for where, row in rows.items()} == LOCKED


# ═══ · parent workflow pins ══════════════════════════════════════════════════════════════════════════════
# Local rollout contract; adopted vendor locks are deliberately independent.

def test_parent_workflow_references_use_reviewed_rollout_commit():
    pins = fleet.parent_refs(ROOT, skip=(".vendor-sync-tools",))
    vendor_tool_pins = Counter(fleet.parent_refs(ROOT)) - Counter(pins)  # the .vendor-sync-tools checkouts
    assert pins, "shared parent references must remain observable"
    assert set(pins) == {PARENT_WORKFLOW_PIN}, pins
    assert vendor_tool_pins and set(vendor_tool_pins) == {VENDOR_TOOL_PIN}, vendor_tool_pins


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
        "frontend-smoke": "3.15",
        "vendor-locked": "${{ matrix.python-version }}"
    },
    "pages.yml": {
        "checks": "3.15",
        "build": "3.15"
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
                    block = fleet.workflow_job(ROOT, name, workflow)
                    self.assertEqual(block.count("uses: " + SETUP_UV), 1)
                    setup = block.index("uses: " + SETUP_UV)
                    command = re.search(
                        r"(?m)^\s*(?:-\s+)?(?:run:\s*)?(?:python(?:3)?|uv)\s+",
                        block,
                    )
                    self.assertIsNotNone(command, "No interpreter consumer was checked")
                    self.assertLess(setup, command.start(), "Python ran before setup-uv")
                    setup_inputs = block[setup:].split("\n", 10)[:9]
                    inputs = "\n".join(setup_inputs)
                    self.assertIn('version: "latest"', inputs)
                    self.assertIn(f'python-version: "{version}"', inputs)
                    self.assertIn("activate-environment: true", inputs)
                    self.assertIn("enable-cache: true", inputs)
                    self.assertIn("save-cache: ${{ github.event_name == 'push' && github.ref == 'refs/heads/main' }}", inputs)  # only main writes
                    self.assertIn("prune-cache: true", inputs)

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
        self.assertIn('python: ["3.11", "3.12", "3.13", "3.14"]', fleet.workflow_job(ROOT, "runtime", "runtime-compatibility.yml"))
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
