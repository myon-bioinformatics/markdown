import markdown as md


def test_mermaid_block_round_trip_and_unicode():
    source = "flowchart TD\n  A[開始] --> B[完了]"
    wrapped = md.mermaid_block(source)

    assert wrapped.startswith("```mermaid\n")
    assert md.extract_mermaid_blocks(wrapped) == [source]


def test_mermaid_block_uses_adaptive_fence_for_backticks():
    source = "sequenceDiagram\n  Note over A: contains ``` here"
    wrapped = md.mermaid_block(source)

    assert wrapped.startswith("````mermaid\n")
    assert md.extract_mermaid_blocks(wrapped) == [source]


def test_extract_mermaid_blocks_keeps_order_and_ignores_other_code():
    document = (
        md.mermaid_block("flowchart LR\n  A --> B")
        + md.code_block("print(1)", lang="python")
        + md.mermaid_block("classDiagram\n  class User")
    )

    assert md.extract_mermaid_blocks(document) == [
        "flowchart LR\n  A --> B",
        "classDiagram\n  class User",
    ]


def test_mermaid_language_match_is_case_insensitive():
    document = "```MERMAID\nflowchart TD\n  A --> B\n```\n"
    assert md.extract_mermaid_blocks(document) == ["flowchart TD\n  A --> B"]


def test_inline_code_and_non_mermaid_fences_are_ignored():
    document = (
        "Use `mermaid` inline.\n\n"
        "```text\nmermaid\n```\n"
    )
    assert md.extract_mermaid_blocks(document) == []


def test_mermaid_block_normalizes_crlf_and_lone_cr():
    source = "flowchart TD\r\n  A --> B\r  B --> C\r\n"
    wrapped = md.mermaid_block(source)

    assert "\r" not in wrapped
    assert md.extract_mermaid_blocks(wrapped) == [
        "flowchart TD\n  A --> B\n  B --> C\n"
    ]


def test_empty_mermaid_source_round_trips():
    assert md.extract_mermaid_blocks(md.mermaid_block("")) == [""]


def test_public_exports_include_mermaid_helpers():
    assert "mermaid_block" in md.__all__
    assert "extract_mermaid_blocks" in md.__all__
