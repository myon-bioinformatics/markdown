import markdown as md


def test_data_uri_preserves_payload_terminal_punctuation():
    cases = [
        ("data:text/plain,Hello!", "data:text/plain,Hello!"),
        ("data:text/plain,Hello?", "data:text/plain,Hello?"),
        ("data:text/plain,hello.", "data:text/plain,hello."),
        ("data:,", "data:,"),
        ("data:text/plain,!!!", "data:text/plain,!!!"),
        ("<data:text/plain,Hello!>", "data:text/plain,Hello!"),
    ]
    for source, expected in cases:
        result = md.extract_data_uris(source)
        assert result[0]["uri"] == expected


def test_data_uri_drops_only_unmatched_markdown_closing_parenthesis():
    result = md.extract_data_uris("(data:text/plain,hello)")
    assert result[0]["uri"] == "data:text/plain,hello"


def test_data_uri_drops_unmatched_paren_followed_by_sentence_punctuation():
    """The common prose case: a data URI in parens at the end of a
    sentence, e.g. "See (data:...,hello)." -- both the unmatched ``)``
    and the trailing "." that was only wrapping it must go, while a
    genuinely balanced payload paren (no imbalance) stays untouched."""
    result = md.extract_data_uris("See (data:text/plain,hello).")
    assert result[0]["uri"] == "data:text/plain,hello"

    balanced = md.extract_data_uris("data:text/plain,a(b)c")
    assert balanced[0]["uri"] == "data:text/plain,a(b)c"


def test_data_uri_rejects_prefixed_false_positives():
    assert md.extract_data_uris("notdata:text/plain,x") == []
    assert md.extract_data_uris("foo_data:text/plain,x") == []


def test_data_uri_keeps_base64_form():
    assert md.extract_data_uris("data:image/png;base64,AAAA") == [{
        "uri": "data:image/png;base64,AAAA",
        "media_type": "image/png",
        "metadata": "image/png;base64",
    }]


def test_data_uri_rejects_metadata_like_non_media_type_headers():
    assert md.extract_data_uris("data:metadata:record,hello") == []


def test_data_uri_uses_text_plain_for_an_omitted_media_type():
    assert md.extract_data_uris("data:,text") == [{
        "uri": "data:,text",
        "media_type": "text/plain",
        "metadata": "",
    }]
