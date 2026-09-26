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


def test_data_uri_keeps_ordinary_payload_bytes_around_unmatched_parens():
    """An imbalanced paren count must not license eating arbitrary trailing
    payload characters -- only ")" and prose punctuation are delimiters;
    anything else stops the strip immediately, even while still imbalanced."""
    cases = [
        ("data:text/plain,a)b", "data:text/plain,a)b"),
        ("data:text/plain,x)y)z", "data:text/plain,x)y)z"),
        ("data:text/plain,payload_with)inside)", "data:text/plain,payload_with)inside"),
        ("data:text/plain,))extra", "data:text/plain,))extra"),
        ("data:text/plain,)hello", "data:text/plain,)hello"),
        ("data:text/plain,a)b)c", "data:text/plain,a)b)c"),
        # A trailing run that contains no ")" at all is never a delimiter
        # run, even if it starts right after an unmatched ")" further back.
        ("data:text/plain,hello)world!", "data:text/plain,hello)world!"),
    ]
    for source, expected in cases:
        result = md.extract_data_uris(source)
        assert result[0]["uri"] == expected, source


def test_data_uri_keeps_payload_punctuation_immediately_before_the_paren():
    """Punctuation that sits *before* an unmatched ")" is payload, not a
    delimiter -- only punctuation trailing *after* the ")" (the prose that
    was wrapping it) gets stripped along with it."""
    cases = [
        ("See (data:text/plain,Hello!).", "data:text/plain,Hello!"),
        ("See (data:text/plain,Hello?).", "data:text/plain,Hello?"),
        ("See (data:text/plain,done.).", "data:text/plain,done."),
        ("(data:text/plain,Hello!)", "data:text/plain,Hello!"),
        ("![x](data:text/plain,Hello!)", "data:text/plain,Hello!"),
    ]
    for source, expected in cases:
        result = md.extract_data_uris(source)
        assert result[0]["uri"] == expected, source


def test_data_uri_trailing_backslash_is_kept():
    """rstrip() here only removes surrounding quote/angle delimiters, same
    as the rest of this module -- a payload ending in "\\" is not one."""
    result = md.extract_data_uris("data:text/plain,ends\\")
    assert result[0]["uri"] == "data:text/plain,ends\\"


def test_data_uri_strips_all_excess_closers_from_stacked_wrappers():
    """A prose paren wrapping a Markdown link/image leaves 2+ unmatched
    ")" at the end -- the cut must remove all of the excess, not just the
    single rightmost one, while still keeping a genuinely balanced payload
    paren that sits inside that excess."""
    cases = [
        ("(see ![x](data:text/plain,hello))", "data:text/plain,hello"),
        ("(see ![x](data:text/plain,a(b)))", "data:text/plain,a(b)"),
        ("((data:text/plain,hello))", "data:text/plain,hello"),
        ("![x](data:text/plain,hello))", "data:text/plain,hello"),
        ("See (data:text/plain,a(b))).", "data:text/plain,a(b)"),
    ]
    for source, expected in cases:
        result = md.extract_data_uris(source)
        assert result[0]["uri"] == expected, source


def test_data_uri_strips_angle_bracket_exposed_by_paren_removal():
    """Removing a wrapping ")" can expose a "<...>"-style delimiter that
    was hidden behind it -- e.g. "(<data:...,x>)" -- and that exposed ">"
    must also be dropped, not left dangling on the observed URI."""
    cases = [
        ("See (<data:text/plain,Hello!>).", "data:text/plain,Hello!"),
        ("(<data:text/plain,Hello!>)", "data:text/plain,Hello!"),
    ]
    for source, expected in cases:
        result = md.extract_data_uris(source)
        assert result[0]["uri"] == expected, source


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
