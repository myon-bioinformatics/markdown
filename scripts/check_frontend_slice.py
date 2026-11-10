"""Fail closed unless the existing browser-free frontend slice is complete."""
from __future__ import annotations

import argparse, sys, xml.etree.ElementTree as ET
from collections import Counter; from pathlib import Path

EXPECTED = {
    "gradio": {
        ("tests.frontend.test_gradio_curl", "test_gradio_curl_matches_direct_call"),
        ("tests.frontend.test_gradio_curl", "test_gradio_curl_empty_input_matches_direct_call"),
        ("tests.frontend.test_gradio_ui", "test_gradio_api_matches_direct_call"),
        ("tests.frontend.test_gradio_ui", "test_gradio_api_empty_input_matches_direct_call"),
    },
    "streamlit": {
        ("tests.frontend.test_streamlit_curl", "test_streamlit_curl_health_and_index"),
        ("tests.frontend.test_streamlit_ui", "test_streamlit_default_fixture_metrics"),
        ("tests.frontend.test_streamlit_ui", "test_streamlit_editing_source_updates_metrics"),
    },
}


def check(frontend: str, path: Path) -> None:
    root = ET.parse(path).getroot()
    cases = root.findall(".//testcase")
    identities = Counter((c.get("classname"), c.get("name")) for c in cases)
    selected = set.union(*EXPECTED.values()) if frontend == "all" else EXPECTED[frontend]
    expected = Counter({identity: 1 for identity in selected})
    if identities != expected:
        raise ValueError(f"Incomplete or unexpected {frontend} test identities: {identities}")
    if any(root.find(f".//{tag}") is not None for tag in ("skipped", "failure", "error")):
        raise ValueError("Frontend slice must have zero skips, failures, and errors")
    print(f"{frontend}: {len(cases)} expected tests passed, zero skips")


def main(argv=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("frontend", choices=(*EXPECTED, "all"))
    parser.add_argument("junit", type=Path)
    args = parser.parse_args(argv)
    check(args.frontend, args.junit)


if __name__ == "__main__":
    raise SystemExit(main())
