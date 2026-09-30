"""Map every HTML benchmark fixture to both required shared PNG checks."""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]


def required_images(out: Path, provenance: Path) -> list[Path]:
    entries = yaml.safe_load(provenance.read_text(encoding="utf-8"))["benchmark_fixtures"]
    ids = [item["id"] for item in entries if item["path"].endswith(".html")]
    if not ids or len(ids) != len(set(ids)):
        raise ValueError("expected a nonempty unique set of HTML fixture identities")
    for identity in ids:
        if not isinstance(identity, str) or Path(identity).name != identity or identity in {".", ".."}:
            raise ValueError("fixture identity must be a directory name")
    return [out / identity / filename for identity in ids for filename in ("original.png", "roundtrip.png")]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", type=Path)
    parser.add_argument("--kit", type=Path, required=True)
    parser.add_argument("--provenance", type=Path, default=ROOT / "fixtures/provenance.yaml")
    parser.add_argument("--sha")
    parser.add_argument("--run-id")
    parser.add_argument("--run-attempt")
    parser.add_argument("--stage", choices=("complete", "failed"))
    args = parser.parse_args(argv)
    images = required_images(args.out, args.provenance)
    if args.stage:
        if not all((args.sha, args.run_id, args.run_attempt)):
            parser.error("receipt mode requires SHA, run ID and attempt")
        identities = ["--sha", args.sha, "--run-id", args.run_id, "--run-attempt", args.run_attempt,
                      "--captures", "original.png,roundtrip.png"]
        expected = []
        failed = False
        for directory in dict.fromkeys(image.parent for image in images):
            project = "chromium-" + directory.name
            expected.append(project)
            result = subprocess.run([sys.executable, "-S", str(args.kit / "scripts/write_capture_evidence.py"),
                str(directory), "--project", project, "--stage", args.stage, *identities], check=False)
            failed = failed or result.returncode != 0
        checker = subprocess.run([sys.executable, "-S", str(args.kit / "scripts/check_capture_evidence.py"),
            str(args.out), "--expect", ",".join(expected), *identities], check=False)
        if failed or checker.returncode:
            return 1
        return subprocess.run([sys.executable, "-S", str(args.kit / "scripts/probe_capture_rejections.py"),
            str(args.out), "--expect", ",".join(expected), *identities], check=False).returncode
    return subprocess.run([sys.executable, "-S", str(args.kit / "scripts/check_png.py"),
                           *map(str, images)], check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
