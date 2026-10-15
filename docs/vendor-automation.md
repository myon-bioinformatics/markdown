# Public vendor placement in CI

Push and pull request CI verifies `vendor.lock.json` with the pinned shared
`vendor_sync.py`, then recreates locked vendor files from their recorded commits
and verifies again. There is no upstream auto-update, promotion, or per-file
provenance sidecar in this repository: `vendor.lock.json` is the only
provenance record.

The shared tool is checked out from `myon-bioinformatics/myon-bioinformatics` at
`9cc33f08f225eaf67d9a00489a1bf15977ebee25`. Checkout credentials are not
persisted.

`vendor.lock.json` is the acquisition contract: each entry's `ref` is a full
40-character commit SHA equal to `commit`, with Git blob and SHA-256 hashes for
every vendored byte. Local tests in `tests/test_vendor_lock.py` cross-check
those hashes against the checked-in tree.

## Local verification

```bash
set -euo pipefail
git clone https://github.com/myon-bioinformatics/myon-bioinformatics.git .vendor-sync-tools
git -C .vendor-sync-tools checkout --detach 9cc33f08f225eaf67d9a00489a1bf15977ebee25
python -S .vendor-sync-tools/vendor_sync.py check --manifest vendor.lock.json
```

Run the existing Python suite with its test-only dependencies after verification.

## What a green run covers

`resolve-vendor` performs check → materialize → check on one Python version.
The primary `pytest` matrix and the independent `test-locked` job on Python 3.12
each verify the lock, load vendored `gh_identity.py` under `python -S`, and run
the suite. Pages/Docker continue shipping checked-in bytes; nothing is written
back to main.

## Retired Ironmate sources

Ironmate #81 removed its root metadata/provenance prototypes. This consumer's
Ironmate LICENSE entry resolves its already-verified full commit SHA instead of
moving main. Source bytes and hashes remain unchanged.
