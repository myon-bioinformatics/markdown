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
    args = parser.parse_args(argv)
    images = required_images(args.out, args.provenance)
    return subprocess.run([sys.executable, "-S", str(args.kit / "scripts/check_png.py"),
                           *map(str, images)], check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
