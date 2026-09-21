from __future__ import annotations

import argparse
import types

import pytest

import markdown as md


def test_inspect_to_markdown_function_reference_is_deterministic():
    def sample(value, flag=False):
        """Return a sample value.

        Longer documentation stays in the description section.
        """
        return str(value)

    first = md.inspect_to_markdown(sample, title="Sample API")
    second = md.inspect_to_markdown(sample, title="Sample API")

    assert first == second
    assert first.startswith("# Sample API\n")
    assert "| Kind | function |" in first
    assert "## Description" in first
    assert "Return a sample value." in first
    assert "(value, flag=False)" in first


def test_inspect_to_markdown_class_does_not_invoke_properties():
    class Safe:
        """Safe API."""

        @property
        def dangerous(self):
            raise AssertionError("property must not be invoked")

        def run(self, value):
            """Run one value."""
            return value

        @staticmethod
        def helper(item):
            """Help with an item."""
            return item

    result = md.inspect_to_markdown(Safe)

    assert "dangerous" not in result
    assert "| run | function | (self, value) | Run one value. |" in result
    assert "| helper | function | (item) | Help with an item. |" in result


def test_inspect_to_markdown_module_lists_only_owned_public_api():
    module = types.ModuleType("demo_module")

    def owned(value):
        """Owned function."""
        return value

    def imported(value):
        return value

    owned.__module__ = "demo_module"
    imported.__module__ = "other_module"
    module.owned = owned
    module.imported = imported
    module._private = owned

    result = md.inspect_to_markdown(module)

    assert "| owned | function | (value) | Owned function. |" in result
    assert "imported" not in result
    assert "_private" not in result


def test_argparse_to_markdown_documents_arguments_and_subcommands():
    parser = argparse.ArgumentParser(
        prog="demo",
        description="Demo CLI.",
        epilog="Done.",
    )
    parser.add_argument("path", help="Input path")
    parser.add_argument("--mode", choices=["fast", "safe"], default="safe", help="Run mode")
    parser.add_argument("--count", type=int, required=True, help="Count")

    subs = parser.add_subparsers(dest="command")
    child = subs.add_parser("serve", description="Serve content")
    child.add_argument("--port", type=int, default=8000)

    result = md.argparse_to_markdown(parser)

    assert result.startswith("# CLI: demo\n")
    assert "## Usage" in result
    assert "| path | no |" in result
    assert "| --mode | no |  | fast, safe | safe | Run mode |" in result
    assert "| --count | yes |" in result
    assert "## Subcommands" in result
    assert "| serve | Serve content |" in result
    assert "## Epilog" in result
    assert result == md.argparse_to_markdown(parser)


def test_argparse_to_markdown_rejects_non_parser():
    with pytest.raises(TypeError, match="ArgumentParser"):
        md.argparse_to_markdown(object())


class _FakeMetadata(dict):
    def get_all(self, key):
        if key == "Project-URL":
            return ["Docs, https://example.test/docs", "Source, https://example.test/src"]
        return None


class _FakeEntryPoint:
    def __init__(self, group, name, value):
        self.group = group
        self.name = name
        self.value = value


class _FakeDistribution:
    version = "1.2.3"
    requires = ["zeta>=1", "alpha"]

    def __init__(self):
        self.metadata = _FakeMetadata(
            {
                "Name": "demo-package",
                "Summary": "Demo package.",
                "Requires-Python": ">=3.9",
            }
        )
        self.entry_points = [
            _FakeEntryPoint("console_scripts", "zeta", "demo:zeta"),
            _FakeEntryPoint("console_scripts", "alpha", "demo:alpha"),
        ]


def test_distribution_to_markdown_is_deterministic_and_sorted(monkeypatch):
    monkeypatch.setattr(
        md.importlib_metadata,
        "distribution",
        lambda name: _FakeDistribution(),
    )

    result = md.distribution_to_markdown("demo-package")

    assert result.startswith("# Package: demo-package\n")
    assert "| Version | 1.2.3 |" in result
    assert "## Project URLs" in result
    assert result.index("Docs") < result.index("Source")
    assert "## Requires" in result
    assert result.index("- alpha") < result.index("- zeta>=1")
    assert "## Entry Points" in result
    assert result.index("| console_scripts | alpha |") < result.index("| console_scripts | zeta |")
    assert result == md.distribution_to_markdown("demo-package")


def test_distribution_to_markdown_missing_distribution(monkeypatch):
    def missing(name):
        raise md.importlib_metadata.PackageNotFoundError(name)

    monkeypatch.setattr(md.importlib_metadata, "distribution", missing)

    with pytest.raises(ValueError, match="Distribution not found"):
        md.distribution_to_markdown("missing-package")


def test_distribution_to_markdown_rejects_empty_name():
    with pytest.raises(ValueError, match="non-empty"):
        md.distribution_to_markdown("   ")
