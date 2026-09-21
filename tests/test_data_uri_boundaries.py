import markdown as md


def test_data_uri_trims_common_terminal_prose_punctuation():
    result = md.extract_data_uris("See data:text/plain,hello.")

    assert result[0]["uri"] == "data:text/plain,hello"


def test_data_uri_rejects_metadata_like_non_media_type_headers():
    assert md.extract_data_uris("data:metadata:record,hello") == []


def test_data_uri_uses_text_plain_for_an_omitted_media_type():
    assert md.extract_data_uris("data:,text") == [{
        "uri": "data:,text",
        "media_type": "text/plain",
        "metadata": "",
    }]
