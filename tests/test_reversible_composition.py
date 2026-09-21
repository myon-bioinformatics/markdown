"""Negative-space tests for explicit reversible converter composition.

Positive F/G/H identity cycles are already covered by
scripts/converter_contract_audit.py and test_converter_contract_audit.py.
This file intentionally keeps only composition boundaries that should fail or
remain structurally distinct, avoiding duplicated positive fixtures.
"""

from __future__ import annotations

import pytest

import markdown as md


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
