"""Local rollout contract; adopted vendor locks are deliberately independent."""
import re
from pathlib import Path

PARENT = "myon-bioinformatics/myon-bioinformatics"
PARENT_WORKFLOW_PIN = "9e3da7ae1846e9604ebc24bb5178f7de094a4e77"
VENDOR_TOOL_PIN = "26c442bc51b8a2837fe2556782b2937f396932af"
ROOT = next(p for p in Path(__file__).resolve().parents if (p / ".github/workflows").is_dir())


def test_parent_workflow_references_use_reviewed_rollout_commit():
    pins = []
    vendor_tool_pins = []
    for path in sorted((ROOT / ".github/workflows").glob("*")):
        if path.suffix not in (".yml", ".yaml"):
            continue
        text = path.read_text(encoding="utf-8")
        # Capture mutable and shortened reusable-workflow references too.
        pins.extend(re.findall(r"uses:\\s*['\\"]?" + re.escape(PARENT) + r"/[^\\s@'\\"]+@([^\\s'\\"]+)", text))
        lines = text.splitlines()
        for i, line in enumerate(lines):
            if not re.fullmatch(r"\\s+repository:\\s*['\\"]?" + re.escape(PARENT) + r"['\\"]?\\s*", line):
                continue
            block = lines[i + 1:i + 12]
            refs = [re.fullmatch(r"\\s+ref:\\s*['\\"]?([^\\s'\\"]+)['\\"]?\\s*", item) for item in block]
            ref = next((m.group(1) for m in refs if m), None)
            if any(re.fullmatch(r"\\s+path:\\s*['\\"]?\\.vendor-sync-tools['\\"]?\\s*", item) for item in block):
                vendor_tool_pins.append(ref)
            else:
                pins.append(ref)
    assert pins, "shared parent references must remain observable"
    assert set(pins) == {PARENT_WORKFLOW_PIN}, pins
    assert vendor_tool_pins and set(vendor_tool_pins) == {VENDOR_TOOL_PIN}, vendor_tool_pins
