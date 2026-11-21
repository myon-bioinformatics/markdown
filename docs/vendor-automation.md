# Public vendor placement in CI

Push and pull request CI verifies `vendor.lock.json` with the pinned shared
`vendor_sync.py`, then recreates locked vendor files from their recorded commits
and verifies again. There is no upstream auto-update, promotion, or per-file
provenance sidecar in this repository: `vendor.lock.json` is the only
provenance record.

The shared tool is checked out from `myon-bioinformatics/myon-bioinformatics`.
Use the full `ref` from the `resolve-vendor` job's **Fetch pinned shared vendor
tool** step in [CI](../.github/workflows/ci.yml). Checkout credentials are not
persisted.

`vendor.lock.json` is the acquisition contract: each entry's `ref` is a full
40-character commit SHA equal to `commit`, with Git blob and SHA-256 hashes for
every vendored byte. Local tests in `tests/test_fleet.py` use the parent's
`vendor/fleet_check.py` to check every locked destination against the checked-in
bytes. The tests also reject duplicate destinations, ignoring case, and require
the named bindings for Markdown's vendored tooling and retained licenses. An
additional valid destination does not require changing that list.

## Local verification

Set `VENDOR_SYNC_REF` to the full SHA copied from the CI step above.

```bash
set -euo pipefail
: "${VENDOR_SYNC_REF:?Copy the full vendor tool ref from CI}"
[[ "$VENDOR_SYNC_REF" =~ ^[0-9a-f]{40}$ ]]
git clone https://github.com/myon-bioinformatics/myon-bioinformatics.git .vendor-sync-tools
git -C .vendor-sync-tools checkout --detach "$VENDOR_SYNC_REF"
python -S .vendor-sync-tools/vendor_sync.py check --manifest vendor.lock.json
python -S .vendor-sync-tools/vendor_sync.py recreate --manifest vendor.lock.json
```

Run `recreate` in an isolated checkout. It fetches each locked file into empty
staging, verifies the staged bytes, replaces checked-in copies, and rechecks
them. The manifest is not updated.

Run the existing Python suite with its test-only dependencies after verification:

```bash
uv sync --locked --group dev
uv run pytest
```

## What a green run covers

`resolve-vendor` runs `check`, then `recreate`, on one Python version.
The primary `test` matrix and the independent `vendor-locked` job on Python 3.12
each verify the lock, load vendored `gh_identity.py` under `python -S`, and run
the suite. Pages/Docker continue shipping checked-in bytes; nothing is written
back to main.

## Retired Ironmate sources

Ironmate #81 removed its root metadata/provenance prototypes. This consumer's
Ironmate LICENSE entry resolves its already-verified full commit SHA instead of
moving main. Source bytes and hashes remain unchanged.
