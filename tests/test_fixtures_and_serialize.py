from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import markdown as md

FIXTURES = ROOT / "fixtures"


def _load_provenance() -> dict:
    return yaml.safe_load((FIXTURES / "provenance.yaml").read_text(encoding="utf-8"))


def test_real_world_fixtures_against_provenance() -> None:
    data = _load_provenance()
    for item in data["fixtures"]:
        content = (FIXTURES / item["path"]).read_text(encoding="utf-8")
        inv = md.inventory(content)
        expect = item["expect"]
        assert inv["heading_count"] >= expect["min_headings"], item["id"]
        assert inv["image_count"] >= expect["min_images"], item["id"]
        assert inv["link_count"] >= expect["min_links"], item["id"]
        assert inv["code_block_count"] >= expect["min_code_blocks"], item["id"]
        if expect.get("has_horizontal_rule"):
            assert inv["horizontal_rule_count"] >= 1, item["id"]
        if expect.get("has_reference_links"):
            assert any(link.get("style") == "reference" for link in inv["links"]), item["id"]
        for tag in expect.get("has_raw_html_tags", []):
            assert any(h["tag"] == tag for h in inv["raw_html"]), (item["id"], tag)


def test_unsupported_constructs_are_documented() -> None:
    data = _load_provenance()
    notes = {row["name"]: row["note"] for row in data["unsupported_examples"]}
    assert "task_list" in notes
    task = next(row for row in data["unsupported_examples"] if row["name"] == "task_list")
    task_html = md.markdown_to_html(task["markdown"])
    # Task lists stay literal list text; no checkbox <input>.
    assert "<input" not in task_html.lower()


def test_gfm_table_example_now_renders() -> None:
    data = _load_provenance()
    example = next(row for row in data["supported_examples"] if row["name"] == "gfm_table")
    html = md.markdown_to_html(example["markdown"])
    assert "<table>" in html
    assert "<th>a</th>" in html
    assert "<td>1</td>" in html


def test_json_fixture_roundtrip_helpers() -> None:
    payload = json.loads((FIXTURES / "roundtrip.json").read_text(encoding="utf-8"))
    rt = payload["roundtrip"]
    assert md.html_image_to_markdown(rt["html_image"]) == rt["markdown_image"]
    assert md.html_link_to_markdown(rt["html_link"]) == rt["markdown_link"]
    inv_keys = payload["sample_inventory_keys"]
    sample = (FIXTURES / "kubernetes_readme_snippet.md").read_text(encoding="utf-8")
    inv = md.inventory(sample)
    for key in inv_keys:
        assert key in inv


def test_yaml_json_toml_serialize_inventory(tmp_path: Path) -> None:
    content = (FIXTURES / "vscode_readme_snippet.md").read_text(encoding="utf-8")
    inv = md.inventory(content)
    slim = {
        "heading_count": inv["heading_count"],
        "link_count": inv["link_count"],
        "image_count": inv["image_count"],
        "urls": inv["urls"],
    }

    yaml_path = tmp_path / "inv.yaml"
    json_path = tmp_path / "inv.json"
    toml_path = tmp_path / "inv.toml"

    yaml_path.write_text(yaml.safe_dump(slim, sort_keys=True), encoding="utf-8")
    json_path.write_text(json.dumps(slim, indent=2), encoding="utf-8")

    # TOML write via stdlib is awkward for nested lists; keep a tiny document.
    toml_path.write_text(
        "[counts]\n"
        f"heading_count = {slim['heading_count']}\n"
        f"link_count = {slim['link_count']}\n"
        f"image_count = {slim['image_count']}\n",
        encoding="utf-8",
    )

    assert yaml.safe_load(yaml_path.read_text(encoding="utf-8"))["heading_count"] == slim[
        "heading_count"
    ]
    assert json.loads(json_path.read_text(encoding="utf-8"))["link_count"] == slim["link_count"]

    tomllib = pytest.importorskip("tomllib")
    loaded = tomllib.loads(toml_path.read_text(encoding="utf-8"))
    assert loaded["counts"]["image_count"] == slim["image_count"]

    meta = tomllib.loads((FIXTURES / "meta.toml").read_text(encoding="utf-8"))
    assert meta["meta"]["name"] == "markdown-single-file"
    assert meta["expect"]["heading_title"] == "Hello"
