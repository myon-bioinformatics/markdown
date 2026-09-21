import markdown as md


def test_headings_to_mermaid_mindmap_and_back():
    source = "# Top\n\n## Child\n"
    mindmap = md.headings_to_mermaid_mindmap(source)

    assert mindmap == "mindmap\n  root((Document))\n    Top\n      Child\n"
    assert md.mermaid_mindmap_to_markdown(mindmap) == source
