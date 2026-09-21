import json
import markdown as md


def test_markdown_to_ipynb_and_back_preserves_markdown_and_python_source():
    source = "# Title\n\n```python\nvalue = 1\n```\n"
    notebook = json.loads(md.markdown_to_ipynb(source))

    assert [cell["cell_type"] for cell in notebook["cells"]] == ["markdown", "code"]
    assert notebook["cells"][1]["outputs"] == []
    assert md.ipynb_to_markdown(notebook) == source


def test_ipynb_to_markdown_rejects_non_notebook_data():
    try:
        md.ipynb_to_markdown("{}")
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")
