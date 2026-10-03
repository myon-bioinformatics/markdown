# Controlled child pytest evidence

Issue #87 connects actual `markdown.bold()` and `markdown.heading()` calls
to pytest-generated JUnit and the canonical xprobe importer. The fixture has
two intentionally wrong parameterized expectations, one setup error, one pass
and one skip. Both JUnit modes must report those same counts and exit 1.
The outer regression is green only when the expected failures are verified.
Unexpected outer suite failures still fail the ordinary CI test step.

The test imports xprobe fetched by the main pytest job at commit
`7e7015b2df69ad446b968f6fa49711b5b1dbdd3f`, Git blob
`dbc5b7d55005d6288c072a7612584d6170c216f4`, verifying the bytes before import.
This is the existing ascii_artist importer pin, sufficient for this API.
No runtime dependency is added. Generic native/receipt/classification coverage
stays in [xprobe #7](https://github.com/myon-bioinformatics/xprobe/pull/7);
the domain integration follows [ascii_artist #27](https://github.com/myon-bioinformatics/ascii_artist/pull/27).

Raw XML must contain the dummy parameter/message/stdout/stderr/setup sentinels;
the three compact failure/error identities must omit them. Both parameterized
failures are retained even though their display names collapse. Compact identity
does not reconstruct inputs or prove learning. Canonical commit identity is null.

CI preserves raw XML and the child exit status before importer/assertion checks,
and compact JSONL as soon as it is computed. Separate
`controlled-failure-py*` Actions artifacts have 14-day retention. They do not
match the ordinary `junit-py*` pattern, so the existing canonical reusable
collector pin and exact six-report set stay unchanged.
Raw evidence is never published to Pages. Public repository Actions artifacts
are downloadable by signed-in users; the controlled fixture uses dummy data.
Timeouts before child completion are not covered by this example's retention.

To run locally, fetch and verify `build/shared/xprobe.py` using the
`Fetch pinned xprobe JUnit importer` step in `.github/workflows/ci.yml`,
install `requirements-dev.txt`, then run:

```sh
PYTHONPATH=build/shared python -m pytest -q
```

Optionally set `MARKDOWN_FAILURE_EVIDENCE` to a new output directory to retain
child reports; reuse is rejected to avoid mixing old and new evidence.
No importer download occurs inside tests, and a missing importer is a collection
error rather than a silently skipped regression. The standalone frontend and
Pages test selections do not require this importer.
