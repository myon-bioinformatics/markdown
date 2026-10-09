"""Retired upstream paths keep immutable identities and verified bytes."""
import hashlib
import json
from pathlib import Path


def test_ironmate_legacy_sources_keep_exact_refs_and_bytes():
    root = Path(__file__).resolve().parents[1]
    entries = [entry for entry in json.loads((root / 'vendor.lock.json').read_text())['files']
               if entry['repository'] == 'myon-bioinformatics/Ironmate']
    assert {e['source'] for e in entries} == {
        'python_artifact_provenance.py', 'repository_metadata_contract.py',
        'repository_metadata_generator.py', 'LICENSE'}
    for entry in entries:
        assert entry['ref'] == entry['commit']
        data = (root / entry['destination']).read_bytes()
        assert hashlib.sha256(data).hexdigest() == entry['sha256']
        assert hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() == entry['blob_sha']
