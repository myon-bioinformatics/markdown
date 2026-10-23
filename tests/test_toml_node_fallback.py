"""toml_to_markdown without tomllib: Node + smol-toml must give the same document."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

import markdown as md

MODULES = Path(__file__).resolve().parent / "mirror" / "node_modules"
needs_node = pytest.mark.skipif(shutil.which("node") is None or not (MODULES / "smol-toml").is_dir(),
                                reason="run `npm ci --prefix tests/mirror` to enable the Node TOML reader")
SOURCE = ('title = "TOML Example"\nenabled = true\nratio = 1.25\nports = [8000, 8001]\nbig = 9007199254740993\n'
          '[owner]\nname = "妙本"\n[database]\ndata = [["delta", "phi"], [3.14]]\n'
          '[[products]]\nname = "Hammer"\nsku = 738594937\n')


@pytest.fixture()
def node_only(monkeypatch):
    monkeypatch.setenv("NODE_PATH", str(MODULES))
    monkeypatch.setattr(md, "tomllib", None)
    monkeypatch.setattr(md, "_TOML_READER", [])
    md._node_launch_module().clear_probe_cache()
    yield


def _write_fake_node(tmp_path: Path, *, version: str, on_eval: str) -> Path:
    script = tmp_path / "fake_node.py"
    script.write_text(
        "#!/usr/bin/env python3\n"
        "import sys\n"
        f'if len(sys.argv) >= 2 and sys.argv[1] == "--version":\n'
        f'    print("{version}")\n'
        "    raise SystemExit(0)\n"
        'if len(sys.argv) >= 2 and sys.argv[1] == "-e":\n'
        f"    {on_eval}\n"
        "raise SystemExit(2)\n",
        encoding="utf-8",
    )
    os.chmod(script, 0o755)
    return script


def _use_fake_node(monkeypatch, script: Path) -> None:
    monkeypatch.setattr(md, "tomllib", None)
    monkeypatch.setattr(md, "_TOML_READER", [])
    monkeypatch.setenv("NODE", str(script))
    md._node_launch_module().clear_probe_cache()


@needs_node
def test_node_reader_matches_tomllib(node_only):
    assert md.toml_reader() == "node"
    document = md.toml_to_markdown(SOURCE)
    assert md.markdown_to_structured(document)["big"] == 9007199254740993
    if sys.version_info >= (3, 11):
        import tomllib
        assert md.markdown_to_structured(document) == tomllib.loads(SOURCE)


@needs_node
@pytest.mark.parametrize("source,expected", [
    ("values = [9007199254740991, 9007199254740992, 9007199254740993, "
     "-9007199254740993, 9223372036854775807, -9223372036854775808]\n",
     {"values": [9007199254740991, 9007199254740992, 9007199254740993,
                 -9007199254740993, 9223372036854775807, -9223372036854775808]}),
    ("values = [1.0, -0.0, 1e3, 9007199254740992.0, 5e-324]\n",
     {"values": [1.0, -0.0, 1000.0, 9007199254740992.0, 5e-324]}),
    ('x = {"\\u0000int" = "42"}\n', {"x": {"\u0000int": "42"}}),
    ('x = {"\\u0000int" = "not an integer"}\n', {"x": {"\u0000int": "not an integer"}}),
    ('[[items]]\nvalue = 9007199254740993\nratio = 1.0\n'
     '[items.nested]\n"\\u0000int" = "42"\n',
     {"items": [{"value": 9007199254740993, "ratio": 1.0, "nested": {"\u0000int": "42"}}]}),
])
def test_node_reader_preserves_numeric_types_and_literal_keys(node_only, source, expected):
    document = md.toml_to_markdown(source)
    # Canonical documents distinguish int/float and the sign of zero, unlike ==.
    assert document == md.structured_to_markdown(expected, title="TOML")
    if sys.version_info >= (3, 11):
        import tomllib
        assert document == md.structured_to_markdown(tomllib.loads(source), title="TOML")


@needs_node
def test_node_reader_keeps_the_reversible_subset_and_errors(node_only):
    with pytest.raises(ValueError, match="outside the reversible structured subset"):
        md.toml_to_markdown("when = 1979-05-27\n")
    with pytest.raises(ValueError, match="outside the reversible structured subset"):
        md.toml_to_markdown("x = inf\n")
    with pytest.raises(ValueError, match="Invalid TOML"):
        md.toml_to_markdown("a = \n")


def test_no_reader_names_both_options(monkeypatch):
    monkeypatch.setattr(md, "tomllib", None)
    monkeypatch.setattr(md, "_TOML_READER", [])
    monkeypatch.setattr(shutil, "which", lambda name, **kw: None)
    md._node_launch_module().clear_probe_cache()
    assert md.toml_reader() is None
    with pytest.raises(RuntimeError, match=r"tomllib.*Node 24\+.*smol-toml"):
        md.toml_to_markdown("a = 1\n")


def test_node_20_is_rejected_as_reader(tmp_path, monkeypatch):
    script = _write_fake_node(tmp_path, version="v20.0.0", on_eval="pass")
    _use_fake_node(monkeypatch, script)
    assert md.toml_reader() is None
    with pytest.raises(RuntimeError, match=r"Node 24\+.*smol-toml"):
        md.toml_to_markdown("a = 1\n")


def test_toml_reader_probe_timeout_reraises_timeout_expired(monkeypatch):
    monkeypatch.setattr(md, "tomllib", None)
    monkeypatch.setattr(md, "_TOML_READER", [])
    node_launch = md._node_launch_module()
    monkeypatch.setattr(node_launch, "resolve_node", lambda **kwargs: "/fake/node")

    def timed_out(*args, **kwargs):
        raise node_launch.LaunchError(
            "node_launch: Node process timed out",
            code="ELAUNCHFAILURE",
            stdout=b"",
            stderr=b"",
        )

    monkeypatch.setattr(node_launch, "run", timed_out)
    with pytest.raises(subprocess.TimeoutExpired) as info:
        md.toml_reader()
    assert info.value.timeout == 30


def test_toml_loads_timeout_reraises_timeout_expired(monkeypatch):
    monkeypatch.setattr(md, "tomllib", None)
    monkeypatch.setattr(md, "_TOML_READER", ["node"])
    node_launch = md._node_launch_module()
    monkeypatch.setattr(node_launch, "resolve_node", lambda **kwargs: "/fake/node")

    def timed_out(*args, **kwargs):
        raise node_launch.LaunchError(
            "node_launch: Node process timed out",
            code="ELAUNCHFAILURE",
            stdout=b"",
            stderr=b"",
        )

    monkeypatch.setattr(node_launch, "run", timed_out)
    with pytest.raises(subprocess.TimeoutExpired) as info:
        md.toml_to_markdown("a = 1\n")
    assert info.value.timeout == 30


def test_toml_loads_stdin_closed_nonzero_surfaces_stderr(tmp_path, monkeypatch):
    script = _write_fake_node(
        tmp_path,
        version="v24.0.0",
        on_eval='import sys; sys.stderr.write("boom\\n"); sys.exit(3)',
    )
    _use_fake_node(monkeypatch, script)
    monkeypatch.setattr(md, "_TOML_READER", ["node"])
    monkeypatch.setattr(md, "tomllib", None)
    with pytest.raises(RuntimeError, match=r"Node TOML reader failed: boom"):
        md.toml_to_markdown("a = 1\n")
