import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import repository_diagnostics as diagnostics


def _locked(destination):
    root = Path(__file__).resolve().parents[1]
    lock = json.loads((root / "vendor.lock.json").read_text(encoding="utf-8"))
    return next(e for e in lock["files"] if e["destination"] == destination)

ROOT = Path(__file__).resolve().parents[1]


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
        path = Path(diagnostics.GENERATOR.record_from_checkout.__globals__["__file__"])
        self.assertEqual(path.resolve(), (ROOT / "scripts/repository_metadata_generator.py").resolve())
        self.assertNotIn(str(ROOT / "vendor"), sys.path)
        ghi_path = Path(diagnostics.GENERATOR.record_from_checkout.__globals__["_GH_IDENTITY"].__file__)
        self.assertEqual(ghi_path.resolve(), (ROOT / "vendor/gh_identity.py").resolve())

    def test_gh_identity_matches_finalized_lock(self):
        entry = _locked("vendor/gh_identity.py")
        path = ROOT / "vendor/gh_identity.py"
        data = path.read_bytes()
        blob = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        self.assertEqual(blob, entry["blob_sha"])
        self.assertEqual(hashlib.sha256(data).hexdigest(), entry["sha256"])

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
            vendor = standalone / "vendor"
            vendor.mkdir()
            shutil.copyfile(ROOT / "vendor/gh_identity.py", vendor / "gh_identity.py")
            shutil.copyfile(ROOT / "scripts/repository_metadata_generator.py", standalone / "repository_metadata_generator.py")
            patched = standalone / "repository_metadata_generator.py"
            text = patched.read_text(encoding="utf-8").replace(
                '_ROOT = Path(__file__).resolve().parents[1]',
                '_ROOT = Path(__file__).resolve().parent',
            )
            patched.write_text(text, encoding="utf-8")
            output = Path(tmp) / "output"
            env = os.environ.copy()
            for name in ("PYTHONPATH", "GITHUB_HEAD_REF", "GITHUB_REF_NAME"):
                env.pop(name, None)
            subprocess.run(
                [sys.executable, "-S", str(patched),
                 "--root", str(root), "--repository", diagnostics.REPOSITORY,
                 "--output-dir", str(output)],
                cwd=standalone, env=env, check=True,
            )
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
