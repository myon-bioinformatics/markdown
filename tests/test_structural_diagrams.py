from __future__ import annotations

import pytest

import markdown as md


def test_heading_tree_to_mermaid_mindmap_ignores_fenced_headings():
    source = (
        "# Root\n"
        "## Child\n"
        "~~~text\n"
        "# not a heading\n"
        "~~~\n"
        "### Grandchild\n"
        "# Next\n"
    )

    assert md.markdown_headings_to_mermaid_mindmap(source, root="Doc") == (
        "mindmap\n"
        '  root["Doc"]\n'
        '    n0["Root"]\n'
        '      n1["Child"]\n'
        '        n2["Grandchild"]\n'
        '    n3["Next"]\n'
    )


def test_task_dependencies_to_mermaid_flowchart():
    source = (
        "- [ ] Build\n"
        "- [x] Test <- Build\n"
        "- [ ] Deploy <- Test, Build\n"
    )

    assert md.markdown_tasks_to_mermaid_flowchart(source) == (
        "flowchart TD\n"
        '  n0["Build"]\n'
        '  n1["Test"]\n'
        '  n2["Deploy"]\n'
        "  n0 --> n1\n"
        "  n1 --> n2\n"
        "  n0 --> n2\n"
    )


def test_task_dependency_rejects_unknown_and_cycles():
    with pytest.raises(ValueError, match="Unknown task dependencies"):
        md.markdown_tasks_to_mermaid_flowchart("- [ ] Deploy <- Build\n")

    cyclic = "- [ ] A <- B\n- [ ] B <- A\n"
    with pytest.raises(ValueError, match="cycle"):
        md.markdown_tasks_to_mermaid_flowchart(cyclic)


def test_task_dependencies_ignore_fenced_examples():
    source = (
        "- [ ] Real\n"
        "~~~markdown\n"
        "- [ ] Fake <- Real\n"
        "~~~\n"
    )
    result = md.markdown_tasks_to_mermaid_flowchart(source)
    assert 'n0["Real"]' in result
    assert "Fake" not in result


def test_python_ast_to_mermaid_class_diagram():
    source = (
        "class Base:\n"
        "    def ping(self, value):\n"
        "        return value\n"
        "\n"
        "class Child(Base):\n"
        "    async def run(self, item):\n"
        "        return item\n"
    )

    assert md.python_to_mermaid_class_diagram(source) == (
        "classDiagram\n"
        '  class c0["Base"] {\n'
        "    ping(value)\n"
        "  }\n"
        '  class c1["Child"] {\n'
        "    run(item)\n"
        "  }\n"
        "  c0 <|-- c1\n"
    )


def test_python_class_diagram_includes_external_base_and_rejects_invalid_source():
    result = md.python_to_mermaid_class_diagram("class Child(pkg.Base):\n    pass\n")
    assert 'class c1["pkg.Base"]' in result
    assert "c1 <|-- c0" in result

    with pytest.raises(ValueError, match="Invalid Python source"):
        md.python_to_mermaid_class_diagram("class broken(")


def test_markdown_links_to_dot_tracks_heading_context_and_ignores_code():
    source = (
        "# Intro\n"
        "[Docs](https://example.com/docs)\n"
        "`[inline](https://ignored.example)`\n"
        "~~~markdown\n"
        "[fenced](https://ignored.example/fenced)\n"
        "~~~\n"
        "## More\n"
        "[Ref][site]\n"
        "\n"
        "[site]: https://example.com/ref\n"
    )

    assert md.markdown_links_to_dot(source) == (
        "digraph markdown_links {\n"
        '  s0 [label="Intro"];\n'
        '  s1 [label="More"];\n'
        '  u0 [label="https://example.com/docs"];\n'
        '  u1 [label="https://example.com/ref"];\n'
        '  s0 -> u0 [label="Docs"];\n'
        '  s1 -> u1 [label="Ref"];\n'
        "}\n"
    )


def test_structural_diagram_outputs_are_deterministic():
    heading_source = "# A\n## B\n"
    task_source = "- [ ] A\n- [ ] B <- A\n"
    python_source = "class A:\n    pass\n"
    link_source = "# A\n[x](https://example.com)\n"

    calls = [
        (md.markdown_headings_to_mermaid_mindmap, heading_source),
        (md.markdown_tasks_to_mermaid_flowchart, task_source),
        (md.python_to_mermaid_class_diagram, python_source),
        (md.markdown_links_to_dot, link_source),
    ]
    for func, source in calls:
        assert func(source) == func(source)
