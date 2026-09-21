from __future__ import annotations

import pytest

import markdown as md


def _canonical_structured_markdown(content: str) -> str:
    """Compare structured-v1 payloads without adapter-specific titles."""
    return md.structured_to_markdown(md.markdown_to_structured(content))


def test_ini_markdown_toml_markdown_ini_is_identity_on_shared_subset():
    x = "[server]\nhost=localhost\nport=8080\n"

    f_x = md.ini_to_markdown(x)
    g_f_x = md.markdown_to_toml(f_x)

    if md.tomllib is None:
        pytest.skip("TOML reader requires Python 3.11+")

    h_g_f_x = md.toml_to_markdown(g_f_x)
    x_back = md.markdown_to_ini(h_g_f_x)

    assert _canonical_structured_markdown(f_x) == _canonical_structured_markdown(h_g_f_x)
    assert x_back == md.markdown_to_ini(f_x)


def test_dotenv_markdown_toml_markdown_dotenv_is_identity_on_shared_subset():
    x = 'NAME="demo"\nMODE="safe"\n'

    f_x = md.dotenv_to_markdown(x)
    g_f_x = md.markdown_to_toml(f_x)

    if md.tomllib is None:
        pytest.skip("TOML reader requires Python 3.11+")

    h_g_f_x = md.toml_to_markdown(g_f_x)
    x_back = md.markdown_to_dotenv(h_g_f_x)

    assert _canonical_structured_markdown(f_x) == _canonical_structured_markdown(h_g_f_x)
    assert x_back == md.markdown_to_dotenv(f_x)


def test_toml_markdown_ini_markdown_toml_is_identity_on_shared_subset():
    if md.tomllib is None:
        pytest.skip("TOML reader requires Python 3.11+")

    x = '[server]\nhost = "localhost"\nport = "8080"\n'

    f_x = md.toml_to_markdown(x)
    g_f_x = md.markdown_to_ini(f_x)
    h_g_f_x = md.ini_to_markdown(g_f_x)
    x_back = md.markdown_to_toml(h_g_f_x)

    assert _canonical_structured_markdown(f_x) == _canonical_structured_markdown(h_g_f_x)
    assert x_back == md.markdown_to_toml(f_x)


def test_toml_markdown_dotenv_markdown_toml_is_identity_on_shared_subset():
    if md.tomllib is None:
        pytest.skip("TOML reader requires Python 3.11+")

    x = 'NAME = "demo"\nMODE = "safe"\n'

    f_x = md.toml_to_markdown(x)
    g_f_x = md.markdown_to_dotenv(f_x)
    h_g_f_x = md.dotenv_to_markdown(g_f_x)
    x_back = md.markdown_to_toml(h_g_f_x)

    assert _canonical_structured_markdown(f_x) == _canonical_structured_markdown(h_g_f_x)
    assert x_back == md.markdown_to_toml(f_x)


def test_cross_domain_composition_fails_instead_of_coercing():
    if md.tomllib is None:
        pytest.skip("TOML reader requires Python 3.11+")

    # A TOML integer is outside dotenv's flat string-value subset.
    x = "count = 3\n"
    f_x = md.toml_to_markdown(x)

    with pytest.raises(ValueError, match="dotenv values must be strings"):
        md.markdown_to_dotenv(f_x)


def test_ini_and_dotenv_are_not_forced_into_same_shape():
    ini_x = "[section]\nkey=value\n"
    dotenv_x = "KEY=value\n"

    ini_md = md.ini_to_markdown(ini_x)
    dotenv_md = md.dotenv_to_markdown(dotenv_x)

    assert md.markdown_to_structured(ini_md) == {"section": {"key": "value"}}
    assert md.markdown_to_structured(dotenv_md) == {"KEY": "value"}
    assert md.markdown_to_structured(ini_md) != md.markdown_to_structured(dotenv_md)
