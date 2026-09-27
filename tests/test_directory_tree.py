from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import markdown as md

CANONICAL = "- src/\n  - app.py\n  - utils/\n    - __init__.py\n- README.md\n"
TREE = {"src": {"app.py": None, "utils": {"__init__.py": None}}, "README.md": None}


def test_exports() -> None:
    for name in (
        "markdown_to_directory_tree",
        "directory_tree_to_markdown",
        "directory_to_markdown",
        "tree_text_to_markdown",
        "markdown_to_tree_text",
        "scaffold_from_markdown",
    ):
        assert name in md.__all__


def test_markdown_list_round_trips_through_tree_data() -> None:
    assert md.markdown_to_directory_tree(CANONICAL) == TREE
    assert md.directory_tree_to_markdown(TREE) == CANONICAL


def test_item_with_children_is_a_directory_even_without_slash() -> None:
    tree = md.markdown_to_directory_tree("- src\n  - app.py\n- empty/\n")
    assert tree == {"src": {"app.py": None}, "empty": {}}


def test_inline_code_labels_four_space_indent_and_fences_are_handled() -> None:
    content = (
        "Layout:\n\n"
        "* `pkg/`\n"
        "    * `__init__.py`\n"
        "\n"
        "```text\n"
        "- not/a/real/entry\n"
        "```\n"
    )
    assert md.markdown_to_directory_tree(content) == {"pkg": {"__init__.py": None}}


@pytest.mark.parametrize(
    "bad",
    [
        "- ../evil\n", "- a/b\n", "- .\n", "- a\\b\n",
        # Not portable to Windows: ADS separator, reserved devices, trailing dot/space, control chars.
        "- a:b\n", "- CON\n", "- con.txt\n", "- Com1\n", "- lpt9.log\n", "- nul .txt\n",
        "- name.\n", "- a?b\n", "- a|b\n", "- a\x01b\n",
        "- \\ a\n", "- `` `x` ``\n",
    ],
)
def test_unsafe_names_are_rejected(bad: str) -> None:
    with pytest.raises(ValueError):
        md.markdown_to_directory_tree(bad)


@pytest.mark.parametrize("bad", [" a", "a ", "`x`", "a\tb", "a\nb"])
def test_tree_writer_rejects_names_that_would_read_back_differently(bad: str) -> None:
    with pytest.raises(ValueError):
        md.directory_tree_to_markdown({bad: None})


@pytest.mark.parametrize("ok", ["console", "COM10", "lpt", "a.b.c", ".env", "CONFIG.md"])
def test_portable_names_near_reserved_ones_are_accepted(ok: str) -> None:
    assert md.markdown_to_directory_tree(f"- {ok}\n") == {ok: None}


def test_scaffold_rejects_non_portable_names_before_creating_anything(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        md.scaffold_from_markdown("- ok/\n  - a:b\n", tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_duplicate_entries_are_rejected() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        md.markdown_to_directory_tree("- a.txt\n- a.txt\n")


def test_tree_text_round_trip_unicode() -> None:
    text = md.markdown_to_tree_text(CANONICAL)
    assert text == (
        ".\n"
        "├── src/\n"
        "│   ├── app.py\n"
        "│   └── utils/\n"
        "│       └── __init__.py\n"
        "└── README.md\n"
    )
    assert md.tree_text_to_markdown(text) == CANONICAL


def test_tree_text_accepts_ascii_connectors_and_ignores_summary() -> None:
    text = ".\n|-- src\n|   `-- app.py\n`-- README.md\n\n1 directory, 2 files\n"
    assert md.tree_text_to_markdown(text) == "- src/\n  - app.py\n- README.md\n"


def test_tree_text_misaligned_levels_raise() -> None:
    with pytest.raises(ValueError, match="aligned"):
        md.tree_text_to_markdown(".\n  ├── bad\n")


def test_directory_to_markdown_is_sorted_and_skips_hidden(tmp_path: Path) -> None:
    (tmp_path / "b").mkdir()
    (tmp_path / "b" / "x.txt").write_text("", encoding="utf-8")
    (tmp_path / "a.txt").write_text("", encoding="utf-8")
    (tmp_path / ".git").mkdir()
    assert md.directory_to_markdown(tmp_path) == "- a.txt\n- b/\n  - x.txt\n"
    assert ".git/" in md.directory_to_markdown(tmp_path, include_hidden=True)
    assert md.directory_to_markdown(tmp_path, max_depth=1) == "- a.txt\n- b/\n"


def test_directory_to_markdown_rejects_non_directory(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        md.directory_to_markdown(tmp_path / "missing")


def test_scaffold_creates_tree_and_is_idempotent(tmp_path: Path) -> None:
    created = md.scaffold_from_markdown(CANONICAL, tmp_path)
    assert created == ["src/", "src/app.py", "src/utils/", "src/utils/__init__.py", "README.md"]
    assert (tmp_path / "src" / "utils" / "__init__.py").is_file()
    assert md.scaffold_from_markdown(CANONICAL, tmp_path) == []
    # Scaffold -> directory -> Markdown closes the loop (sorted listing).
    assert md.markdown_to_directory_tree(md.directory_to_markdown(tmp_path)) == TREE


def test_scaffold_never_overwrites_existing_files(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("keep me", encoding="utf-8")
    md.scaffold_from_markdown("- README.md\n", tmp_path)
    assert (tmp_path / "README.md").read_text(encoding="utf-8") == "keep me"


def test_scaffold_file_directory_collision_raises(tmp_path: Path) -> None:
    (tmp_path / "src").write_text("", encoding="utf-8")
    with pytest.raises(FileExistsError):
        md.scaffold_from_markdown("- src/\n  - app.py\n", tmp_path)


def test_scaffold_rejects_traversal_before_creating_anything(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        md.scaffold_from_markdown("- ok.txt\n- ../escape.txt\n", tmp_path)
    assert not (tmp_path / "ok.txt").exists()
    assert not (tmp_path.parent / "escape.txt").exists()


def test_scaffold_collision_is_detected_before_anything_is_created(tmp_path: Path) -> None:
    (tmp_path / "b").write_text("keep", encoding="utf-8")
    with pytest.raises(FileExistsError):
        md.scaffold_from_markdown("- a/\n  - x\n- b/\n  - y\n", tmp_path)
    assert sorted(p.name for p in tmp_path.iterdir()) == ["b"]
    assert (tmp_path / "b").read_text(encoding="utf-8") == "keep"


def test_scaffold_does_not_create_root_when_validation_fails(tmp_path: Path) -> None:
    root = tmp_path / "new-root"
    with pytest.raises(ValueError):
        md.scaffold_from_markdown("- CON\n", root)
    assert not root.exists()

