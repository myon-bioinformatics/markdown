"""toml_to_markdown without tomllib: Node + smol-toml must give the same document."""
from __future__ import annotations

import shutil
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
    yield


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
    assert md.toml_reader() is None
    with pytest.raises(RuntimeError, match="tomllib.*smol-toml"):
        md.toml_to_markdown("a = 1\n")
