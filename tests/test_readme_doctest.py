import markdown as md


def test_run_markdown_doctest_uses_only_python_fences_and_keeps_line_numbers():
    document = """# Example

```text
>>> 1 + 1
3
```

```pycon
>>> 1 + 1
2
```
"""

    source = md._markdown_doctest_source(document)

    assert source.count("\n") == document.count("\n")
    assert "```" not in source
    assert md.run_markdown_doctest(document).failed == 0


def test_run_markdown_doctest_returns_failure_count_without_a_cli():
    document = """# Example

```python
>>> value = 2
>>> value * 3
6
```
"""

    result = md.run_markdown_doctest(document, name="README.md")

    assert result.attempted == 2
    assert result.failed == 0
