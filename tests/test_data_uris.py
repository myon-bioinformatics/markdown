from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
import markdown as md

def test_data_uri_is_observed_without_decoding_or_network() -> None:
    uri = "data:image/png;base64,iVBORw0KGgo="
    assert md.extract_data_uris(f"![x]({uri})") == [{"uri": uri, "media_type": "image/png", "metadata": "image/png;base64"}]
