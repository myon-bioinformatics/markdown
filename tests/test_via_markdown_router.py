from __future__ import annotations

import pytest

import markdown as md


def test_via_markdown_routes_are_deterministic_and_describe_domains():
    routes = md.via_markdown_routes()
    assert routes == md.via_markdown_routes()
    assert all(route["via"] == "markdown" for route in routes)
    assert all(route["carrier"] == "structured-v1" for route in routes)
    assert all(route["domain"] for route in routes)


def test_ini_to_toml_via_markdown_round_trip():
    source = "[server]\nhost=localhost\nport=8080\n"
    toml = md.convert_via_markdown(source, "ini", "toml")
    back = md.convert_via_markdown(toml, "toml", "ini") if md.tomllib is not None else None

    assert '[server]' in toml
    assert 'host = "localhost"' in toml
    assert 'port = "8080"' in toml
    if md.tomllib is None:
        assert back is None
    else:
        assert back == md.convert_via_markdown(source, "ini", "ini")


def test_dotenv_to_toml_via_markdown_round_trip():
    source = 'NAME="demo"\nMODE="safe"\n'
    toml = md.convert_via_markdown(source, "dotenv", "toml")
    assert 'NAME = "demo"' in toml
    assert 'MODE = "safe"' in toml

    if md.tomllib is not None:
        back = md.convert_via_markdown(toml, "toml", "dotenv")
        assert back == md.convert_via_markdown(source, "dotenv", "dotenv")


def test_toml_source_routes_depend_on_tomllib():
    pairs = {(route["from"], route["to"]) for route in md.via_markdown_routes()}
    if md.tomllib is None:
        assert not any(source == "toml" for source, _ in pairs)
        with pytest.raises(RuntimeError, match="unavailable"):
            md.convert_via_markdown('NAME = "demo"\n', "toml", "dotenv")
    else:
        assert ("toml", "ini") in pairs
        assert ("toml", "dotenv") in pairs


def test_ini_dotenv_structural_coercion_is_not_declared():
    with pytest.raises(ValueError, match="No reversible via-Markdown route"):
        md.convert_via_markdown("[x]\na=b\n", "ini", "dotenv")
    with pytest.raises(ValueError, match="No reversible via-Markdown route"):
        md.convert_via_markdown("A=b\n", "dotenv", "ini")


def test_route_rejects_content_outside_intersection():
    if md.tomllib is None:
        pytest.skip("TOML reader requires Python 3.11+")
    source = 'count = 3\n'
    with pytest.raises(ValueError, match="outside the reversible domain"):
        md.convert_via_markdown(source, "toml", "dotenv")


@pytest.mark.parametrize("name", ["yaml", "xml", "html"])
def test_route_rejects_unknown_formats(name):
    with pytest.raises(ValueError, match="Unsupported via-Markdown source format"):
        md.convert_via_markdown("x", name, "toml")
    with pytest.raises(ValueError, match="Unsupported via-Markdown target format"):
        md.convert_via_markdown("x", "ini", name)
