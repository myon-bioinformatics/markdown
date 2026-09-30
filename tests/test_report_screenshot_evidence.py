"""Consumer mapping regression tests use the real pinned shared checker."""
import importlib.util
import os
from pathlib import Path
import struct
import subprocess
import sys
import zlib

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("report_screenshots", ROOT / "scripts/check_report_screenshots.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def png():
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(b"\0\xff\xff\xff")) + chunk(b"IEND", b""))


@pytest.mark.parametrize("broken", [None, "missing", "truncated"])
def test_every_fixture_requires_both_real_pngs(tmp_path, broken):
    kit = os.environ.get("BROWSER_TEST_KIT")
    if not kit:
        pytest.skip("integration requires the pinned browser-test-kit checkout")
    provenance = tmp_path / "provenance.yaml"
    provenance.write_text("benchmark_fixtures:\n  - {id: first, path: first.html}\n  - {id: second, path: second.html}\n  - {id: ignored, path: readme.md}\n")
    images = module.required_images(tmp_path / "site", provenance)
    assert len(images) == 4
    for image in images:
        image.parent.mkdir(parents=True, exist_ok=True)
        image.write_bytes(png())
    if broken == "missing":
        images[-1].unlink()
    elif broken == "truncated":
        images[-1].write_bytes(png()[:-12])
    result = subprocess.run([sys.executable, str(ROOT / "scripts/check_report_screenshots.py"),
                             str(tmp_path / "site"), "--kit", kit, "--provenance", str(provenance)],
                            capture_output=True, text=True)
    assert (result.returncode == 0) == (broken is None), result.stderr


@pytest.mark.parametrize("entries", ["[]", "[{id: same, path: a.html}, {id: same, path: b.html}]", "[{id: ../escape, path: a.html}]"])
def test_empty_duplicate_or_unsafe_fixture_set_fails(tmp_path, entries):
    path = tmp_path / "provenance.yaml"
    path.write_text("benchmark_fixtures: " + entries)
    with pytest.raises(ValueError):
        module.required_images(tmp_path, path)
