from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import markdown as md


def test_task_item_generator() -> None:
    assert md.task_item("todo") == "- [ ] todo\n"
    assert md.task_item("done", checked=True) == "- [x] done\n"
    assert md.task_item() == "- [ ]\n"
    assert md.task_item(checked=True) == "- [x]\n"


def test_task_list_generator() -> None:
    assert md.task_list(["a", ("b", True)]) == "- [ ] a\n- [x] b\n"
    assert md.task_list([]) == ""


def test_generator_round_trips_to_disabled_checkboxes() -> None:
    html = md.markdown_to_html(md.task_list(["todo", ("done", True)]))
    assert html.startswith("<ul>")
    assert html.endswith("</ul>\n")
    assert '<input type="checkbox" disabled /> todo' in html
    assert '<input type="checkbox" disabled checked /> done' in html
    # Not interactive: no name/id, and disabled is always present.
    assert html.count("disabled") == 2
    assert "onclick" not in html
    assert "<input" in html


def test_checked_is_case_insensitive() -> None:
    html = md.markdown_to_html("- [x] lower\n- [X] upper\n")
    assert html.count("checked") == 2
    assert "<li>" in html


def test_star_and_plus_markers_are_tasks() -> None:
    star = md.markdown_to_html("* [ ] star\n")
    plus = md.markdown_to_html("+ [x] plus\n")
    assert '<input type="checkbox" disabled /> star' in star
    assert '<input type="checkbox" disabled checked /> plus' in plus


def test_mixed_task_and_ordinary_items_stay_one_list() -> None:
    """Smaller contract: mixed ``<li>`` shapes in one ``<ul>``, not split lists."""
    html = md.markdown_to_html("- [ ] task\n- ordinary\n- [x] done\n")
    assert html.count("<ul>") == 1
    assert html.count("</ul>") == 1
    assert '<input type="checkbox" disabled /> task' in html
    assert "<li>ordinary</li>" in html
    assert '<input type="checkbox" disabled checked /> done' in html


def test_adjacent_ordinary_list_without_blank_line_is_still_one_ul() -> None:
    html = md.markdown_to_html("- alpha\n- [ ] beta\n")
    assert html.count("<ul>") == 1
    assert "<li>alpha</li>" in html
    assert "beta" in html


def test_blank_line_starts_a_new_list() -> None:
    html = md.markdown_to_html("- alpha\n\n- [ ] beta\n")
    assert html.count("<ul>") == 2


def test_numbered_checkbox_syntax_is_not_a_task() -> None:
    html = md.markdown_to_html("1. [ ] not a task\n")
    assert "<ol>" in html
    assert "<input" not in html
    assert "[ ] not a task" in html


def test_missing_space_after_bracket_is_not_a_task() -> None:
    html = md.markdown_to_html("- [x]done\n")
    assert "<input" not in html
    assert "[x]done" in html


def test_inline_formatting_inside_task_text() -> None:
    html = md.markdown_to_html("- [ ] see **bold** and `code`\n")
    assert "<strong>bold</strong>" in html
    assert "<code>code</code>" in html
    assert "<input" in html


def test_task_html_is_escaped() -> None:
    html = md.markdown_to_html("- [ ] <script>alert(1)</script>\n")
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "<input" in html


def test_fenced_task_example_stays_code() -> None:
    html = md.markdown_to_html("```\n- [ ] nope\n```\n")
    assert "<input" not in html
    assert "- [ ] nope" in html
