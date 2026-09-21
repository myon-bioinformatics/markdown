import configparser

import pytest

import markdown as md


def _parse(ini_text: str) -> configparser.ConfigParser:
    parser = configparser.ConfigParser(interpolation=None)
    parser.read_string(ini_text)
    return parser


def test_ini_round_trip_preserves_sections_keys_and_values():
    ini_text = (
        "[server]\n"
        "host = localhost\n"
        "port = 8080\n"
        "\n"
        "[client]\n"
        "timeout = 30\n"
    )
    document = md.ini_to_markdown(ini_text)

    assert "## [server]" in document
    assert "## [client]" in document

    parser = _parse(md.markdown_to_ini(document))
    assert parser["server"]["host"] == "localhost"
    assert parser["server"]["port"] == "8080"
    assert parser["client"]["timeout"] == "30"


def test_ini_default_inheritance_stays_structural_not_flattened():
    ini_text = (
        "[DEFAULT]\n"
        "color = blue\n"
        "size = 10\n"
        "\n"
        "[section1]\n"
        "size = 20\n"
        "\n"
        "[section2]\n"
        "shape = circle\n"
    )
    document = md.ini_to_markdown(ini_text)

    # section1 overrides "size" but does not redeclare the inherited "color".
    section1_index = document.index("## [section1]")
    section2_index = document.index("## [section2]")
    section1_body = document[section1_index:section2_index]
    assert '"color"' not in section1_body
    assert '"size"' in section1_body

    parser = _parse(md.markdown_to_ini(document))
    assert parser["section1"]["color"] == "blue"  # inherited from DEFAULT
    assert parser["section1"]["size"] == "20"  # overridden
    assert parser["section2"]["color"] == "blue"  # inherited from DEFAULT
    assert parser["section2"]["shape"] == "circle"
    assert parser.defaults() == {"color": "blue", "size": "10"}


def test_ini_values_with_pipes_backslashes_unicode_and_multiline_are_unambiguous():
    ini_text = (
        "[section]\n"
        "path = C:\\Users\\name\n"
        "choices = a|b|c\n"
        "label = \u65e5\u672c\u8a9e\n"
        "note = line one\n"
        "\tline two\n"
    )
    document = md.ini_to_markdown(ini_text)
    parser = _parse(md.markdown_to_ini(document))

    assert parser["section"]["path"] == "C:\\Users\\name"
    assert parser["section"]["choices"] == "a|b|c"
    assert parser["section"]["label"] == "\u65e5\u672c\u8a9e"
    assert parser["section"]["note"] == "line one\nline two"


def test_ini_to_markdown_disables_interpolation_percent_is_literal():
    ini_text = "[section]\nformat = %(missing)s literal percent %% done\n"
    document = md.ini_to_markdown(ini_text)
    parser = _parse(md.markdown_to_ini(document))

    assert parser["section"]["format"] == "%(missing)s literal percent %% done"


def test_ini_empty_section_produces_empty_table_and_restores():
    ini_text = "[empty]\n"
    document = md.ini_to_markdown(ini_text)
    parser = _parse(md.markdown_to_ini(document))

    assert parser.has_section("empty")
    assert dict(parser.items("empty")) == {}


def test_markdown_to_ini_rejects_section_heading_without_table():
    document = "# INI\n\n## [broken]\n\nNo table here.\n"
    with pytest.raises(ValueError, match="Key/Value table"):
        md.markdown_to_ini(document)
