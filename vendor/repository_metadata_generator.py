#!/usr/bin/env python3
"""Generate canonical repository metadata JSON and JSONL from a Git checkout.

Delegates schema v1 validation and serialization to the vendored gh_identity module.
"""
from __future__ import annotations

import argparse
import importlib.util
from collections.abc import Mapping
from pathlib import Path
from types import ModuleType


def _load_gh_identity() -> ModuleType:
    path = Path(__file__).resolve().parent / "gh_identity.py"
    spec = importlib.util.spec_from_file_location("_vendor_gh_identity_for_generator", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load vendored module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GH_IDENTITY = _load_gh_identity()


def record_from_checkout(
    root: Path,
    full_name: str,
    *,
    env: Mapping[str, str] | None = None,
    github_reported_size_bytes: int | None = None,
    working_tree_bytes: int | None = None,
    release_artifact_bytes: int | None = None,
    tooling: Mapping[str, str] | None = None,
) -> dict:
    measurements = {
        "github_reported_size_bytes": github_reported_size_bytes,
        "working_tree_bytes": working_tree_bytes,
        "release_artifact_bytes": release_artifact_bytes,
    }
    try:
        return _GH_IDENTITY.repository_metadata_v1(
            root,
            repository=full_name,
            env=dict(env) if env is not None else None,
            measurements=measurements,
            tooling=dict(tooling or {}),
        )
    except _GH_IDENTITY.GitInspectionError as exc:
        raise OSError(str(exc)) from exc


def write_metadata(record: dict, output_dir: Path) -> tuple[Path, Path]:
    _GH_IDENTITY.write_repository_metadata(record, output_dir)
    json_path = output_dir / "repository-metadata.json"
    jsonl_path = output_dir / "repository-metadata.jsonl"
    return json_path, jsonl_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True, help="GitHub owner/name")
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    write_metadata(record_from_checkout(args.root.resolve(), args.repository), args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
