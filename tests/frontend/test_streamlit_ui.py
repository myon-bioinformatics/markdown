"""Verify the real Streamlit script's wiring, with no browser at all.

``streamlit.testing.v1.AppTest`` runs ``demos/streamlit_app.py`` exactly as
``streamlit run`` would (same script, same session state), but in-process
and headless — driving widgets and reading rendered output purely through
its Python API. That exercises the actual ``st.metric``/``st.tabs`` wiring
instead of only ``build_view()`` directly (see ``tests/test_demo_logic.py``
for that plain-function-call coverage).
"""

from __future__ import annotations

from pathlib import Path

import pytest

AppTest = pytest.importorskip("streamlit.testing.v1").AppTest

APP_PATH = Path(__file__).resolve().parents[2] / "demos" / "streamlit_app.py"


def test_streamlit_default_fixture_metrics() -> None:
    at = AppTest.from_file(str(APP_PATH)).run(timeout=15)
    assert not at.exception

    metrics = [m.value for m in at.metric]
    assert len(metrics) == 5
    heading_count, link_count, *_ = (int(v) for v in metrics)
    assert heading_count > 0
    assert link_count > 0

    assert [t.label for t in at.tabs] == [
        "Headings",
        "Links",
        "Images",
        "Code blocks",
        "HTML",
    ]


def test_streamlit_editing_source_updates_metrics() -> None:
    at = AppTest.from_file(str(APP_PATH)).run(timeout=15)
    at.text_area[0].set_value("# Only Heading\n\nplain text, no links or images.\n")
    at.run(timeout=15)

    assert not at.exception
    assert [m.value for m in at.metric] == ["1", "0", "0", "0", "0"]
