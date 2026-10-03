# Pages build metadata

`real_world_pages_report.py` adapts the existing vendored canonical
`repository_metadata_generator.record_from_checkout()` head to the flat
`build_meta.json` fields. It reuses the loader/modules in
`repository_diagnostics.py`; vendor files and their provenance pins are unchanged.
No tracked-byte scan or public URL probe is needed for this adaptation.

The keys remain `version`, `sha`, `shortSha`, `ref`, `committedAt`, `subject`,
`commitUrl`, and `dirty`. Version remains null when markdown has no version;
shortSha remains eight characters. Commit URL still requires
`GITHUB_REPOSITORY` and uses `GITHUB_SERVER_URL` or https://github.com.
Normal clean/dirty JSON and Pages labels remain compatible.

## Deliberate differences from the legacy collector

`tests/fixtures/pages_revision_migration.json` records before/after flat payloads.

- SHA, timestamp and subject all refer to checkout HEAD. `GITHUB_SHA` no longer
  overrides that identity (notably when a PR checks out its head while Actions
  reports a merge SHA).
- Ref follows the canonical producer: `GITHUB_HEAD_REF`, then
  `GITHUB_REF_NAME`, then checkout branch. Detached HEAD without Actions ref
  is explicitly `detached`, rather than null.
- If canonical identity acquisition/validation fails, all identity fields are
  null together, with a stderr diagnostic. No environment fallback identity
  or partial mixed revision is published.
- Dirty is a separate read-only `git_inspector.status()` observation. Successful
  complete status gives true/false; failed or truncated status gives null.
  Pages shows `(dirty unknown)` for null instead of appearing clean. A valid
  status can still be measured when identity fails (for example unborn HEAD),
  and identity can remain available when status fails.

There is no local porcelain parser or additional Git/network/mutation API.
The report remains best-effort when Git metadata cannot be measured; callers
can distinguish unknown from clean by checking `dirty is null`.
