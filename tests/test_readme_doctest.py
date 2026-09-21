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


def test_run_markdown_doctest_reports_failures_without_writing_stdout(capsys):
    document = """```python
>>> 1 + 1
3
```
"""

    result = md.run_markdown_doctest(document)

    assert result == (1, 1)
    assert capsys.readouterr().out == ""


def test_run_markdown_doctest_handles_crlf_line_endings():
    """A correct example must not fail just because the source file uses
    CRLF -- doctest.DocTestParser splits on "\\n", so a stray "\\r" left on
    each Python-fence line would attach to the example/want text."""
    document = "# X\r\n\r\n```python\r\n>>> 1 + 1\r\n2\r\n```\r\n"

    result = md.run_markdown_doctest(document)

    assert result.attempted == 1
    assert result.failed == 0
