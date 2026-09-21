import sys

import pytest

import markdown as md


def test_ini_semantic_round_trip_and_canonical_fixed_point():
    source = (
        "# source comment is intentionally lossy\n"
        "[DEFAULT]\n"
        "MixedCase = 100% literal\n"
        "\n"
        "[server]\n"
        "host: localhost\n"
        "message = 日本語\n"
        "multiline = first\n"
        "    second\n"
    )

    document = md.ini_to_markdown(source)
    canonical = md.markdown_to_ini(document)

    assert md.ini_to_markdown(canonical) == document
    assert md.markdown_to_ini(md.ini_to_markdown(canonical)) == canonical
    assert "[DEFAULT]" in canonical
    assert "MixedCase=100% literal" in canonical


def test_ini_rejects_non_string_structured_values():
    document = md.structured_to_markdown({"section": {"port": 8080}})
    with pytest.raises(ValueError, match="values must be strings"):
        md.markdown_to_ini(document)


def test_dotenv_semantic_round_trip_and_canonical_fixed_point():
    source = (
        "# ignored comment\n"
        "export NAME=妙本\n"
        "EMPTY=\n"
        "PIPE=\"a|b\"\n"
        "MULTILINE=\"line\\nbreak\"\n"
        "LITERAL_DOLLAR=$HOME\n"
    )

    document = md.dotenv_to_markdown(source)
    canonical = md.markdown_to_dotenv(document)

    assert md.dotenv_to_markdown(canonical) == document
    assert md.markdown_to_dotenv(md.dotenv_to_markdown(canonical)) == canonical
    assert 'NAME="妙本"' in canonical
    assert 'LITERAL_DOLLAR="$HOME"' in canonical


def test_dotenv_rejects_duplicate_and_invalid_keys():
    with pytest.raises(ValueError, match="Duplicate"):
        md.dotenv_to_markdown("A=1\nA=2\n")
    with pytest.raises(ValueError, match="Invalid dotenv"):
        md.dotenv_to_markdown("BAD-KEY=value\n")


@pytest.mark.skipif(sys.version_info < (3, 11), reason="tomllib is Python 3.11+")
def test_toml_semantic_round_trip_and_canonical_fixed_point():
    source = (
        'title = "TOML Example"\n'
        'enabled = true\n'
        'ratio = 1.25\n'
        'ports = [8000, 8001]\n'
        '\n'
        '[owner]\n'
        'name = "妙本"\n'
        '\n'
        '[database]\n'
        'data = [["delta", "phi"], [3.14]]\n'
        '\n'
        '[[products]]\n'
        'name = "Hammer"\n'
        'sku = 738594937\n'
        '\n'
        '[[products]]\n'
        'name = "Nail"\n'
        'sku = 284758393\n'
    )

    document = md.toml_to_markdown(source)
    canonical = md.markdown_to_toml(document)

    assert md.toml_to_markdown(canonical) == document
    assert md.markdown_to_toml(md.toml_to_markdown(canonical)) == canonical


@pytest.mark.skipif(sys.version_info < (3, 11), reason="tomllib is Python 3.11+")
def test_toml_quoted_keys_and_nested_values_round_trip():
    source = (
        '"a.b" = { "sp ace" = "x|y", nested = { flag = false } }\n'
        'unicode = "日本語"\n'
    )
    document = md.toml_to_markdown(source)
    canonical = md.markdown_to_toml(document)
    assert md.toml_to_markdown(canonical) == document


@pytest.mark.skipif(sys.version_info < (3, 11), reason="tomllib is Python 3.11+")
def test_toml_rejects_datetime_and_non_finite_values():
    with pytest.raises(ValueError, match="outside the reversible"):
        md.toml_to_markdown("when = 2026-09-21T12:00:00Z\n")
    with pytest.raises(ValueError, match="outside the reversible"):
        md.toml_to_markdown("value = inf\n")


def test_markdown_to_toml_rejects_null():
    document = md.structured_to_markdown({"value": None})
    with pytest.raises(ValueError, match="no null"):
        md.markdown_to_toml(document)


def test_toml_reader_requires_python_311_when_tomllib_unavailable(monkeypatch):
    monkeypatch.setattr(md, "tomllib", None)
    with pytest.raises(RuntimeError, match="3.11"):
        md.toml_to_markdown('x = 1\n')



@pytest.mark.parametrize(
    "value",
    [
        {"bad\nsection": {"key": "value"}},
        {"bad\rsection": {"key": "value"}},
        {"section": {"bad\nkey": "value"}},
        {"section": {"bad\rkey": "value"}},
    ],
)
def test_markdown_to_ini_rejects_embedded_newlines_in_names(value):
    document = md.structured_to_markdown(value)
    with pytest.raises(ValueError, match="single-line"):
        md.markdown_to_ini(document)
