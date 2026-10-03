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


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


class RepositoryMetadataProducerTests(unittest.TestCase):
    def test_generator_uses_pinned_contract_without_sys_path_mutation(self):
        path = Path(diagnostics.GENERATOR.build_repository_record.__globals__["__file__"])
        self.assertEqual(path.resolve(), (ROOT / "vendor/repository_metadata_contract.py").resolve())
        self.assertNotIn(str(ROOT / "vendor"), sys.path)

    def test_producer_pair_matches_finalized_source(self):
        expected = {
            "repository_metadata_contract": (
                _locked('vendor/repository_metadata_contract.py')['blob_sha'],
                _locked('vendor/repository_metadata_contract.py')['sha256'],
            ),
            "repository_metadata_generator": (
                _locked('vendor/repository_metadata_generator.py')['blob_sha'],
                _locked('vendor/repository_metadata_generator.py')['sha256'],
            ),
        }
        for name, (blob, digest) in expected.items():
            path = ROOT / "vendor" / (name + ".py")
            provenance = json.loads(path.with_suffix(".provenance.json").read_text())
            self.assertEqual(provenance["source_repository"], "myon-bioinformatics/Ironmate")
            self.assertEqual(provenance["source_path"], name + ".py")
            self.assertEqual(provenance["source_commit"], _locked('vendor/' + name + '.py')['commit'])
            self.assertEqual(provenance["schema_version"], "1.0")
            self.assertEqual(provenance["blob_sha"], blob)
            self.assertEqual(git_blob_sha(path), blob)
            self.assertEqual(provenance["sha256"], digest)
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), digest)

    def test_producer_pair_validates_distinct_source_commits(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            entries = {}
            for index, name in enumerate(("repository_metadata_contract", "repository_metadata_generator"), 1):
                destination = "vendor/" + name + ".py"
                entry = dict(_locked(destination), commit=str(index) * 40)
                entries[destination] = entry
                path = root / destination
                path.parent.mkdir(exist_ok=True)
                shutil.copyfile(ROOT / destination, path)
                record = json.loads((ROOT / destination).with_suffix(".provenance.json").read_text(encoding="utf-8"))
                record["source_commit"] = entry["commit"]
                path.with_suffix(".provenance.json").write_text(json.dumps(record), encoding="utf-8")
            with mock.patch.dict(globals(), {"ROOT": root, "_locked": lambda destination: entries[destination]}):
                self.test_producer_pair_matches_finalized_source()

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
                expected = diagnostics.CONTRACT.build_repository_record(
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
                self.assertEqual(json.loads(diagnostics.CONTRACT.to_jsonl(record)), expected)
            git("checkout", "--detach", "-q")
            with mock.patch.object(diagnostics, "ROOT", root):
                detached = diagnostics.build_record({}, generated_at=now)
                with self.assertRaises(ValueError):
                    diagnostics.build_record({}, generated_at="invalid timestamp")
            self.assertEqual(detached["head"]["branch"], "detached")
            self.assertEqual(detached["head"]["sha"], head)

            standalone = Path(tmp) / "standalone"
            standalone.mkdir()
            for name in ("repository_metadata_contract.py", "repository_metadata_generator.py"):
                shutil.copyfile(ROOT / "vendor" / name, standalone / name)
            output = Path(tmp) / "output"
            env = os.environ.copy()
            for name in ("PYTHONPATH", "GITHUB_HEAD_REF", "GITHUB_REF_NAME"):
                env.pop(name, None)
            subprocess.run(
                [sys.executable, "-S", str(standalone / "repository_metadata_generator.py"),
                 "--root", str(root), "--repository", diagnostics.REPOSITORY,
                 "--output-dir", str(output)],
                cwd=tmp, env=env, check=True,
            )
            direct = json.loads((output / "repository-metadata.json").read_text())
            self.assertEqual(direct["head"], detached["head"])
            self.assertEqual(json.loads((output / "repository-metadata.jsonl").read_text()), direct)
            self.assertIsNone(direct["measurements"]["working_tree_bytes"])

    def test_payload_preserves_resolver_and_unsupported_ref_behavior(self):
        record = diagnostics.CONTRACT.build_repository_record(
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
