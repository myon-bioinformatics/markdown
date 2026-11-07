# PR #38 implementation contract: legacy HTML URL safety parity

Refs #24 and follows #36 / #37.

## Goal

Close the first **observed final-Markdown gap** recorded by the converter integration scaffold:

- legacy `html_to_markdown()` may preserve unsafe `href` / `src`
- DOM conversion removes unsafe URL schemes before the shared HTML→Markdown engine sees them

PR #38 should make the legacy HTML→Markdown path follow the same URL safety contract as the DOM path **without switching `html_to_markdown()` to DOM-first**.

## Required behavior

Use the existing shared `_sanitize_url_scheme()` policy as the source of truth.

For HTML→Markdown conversion:

- safe `http` / `https` / `mailto` URLs remain links
- relative URLs remain supported
- the host:port normalization contract from #36 remains intact where applicable
- unsafe absolute schemes such as `javascript:`, `data:`, and `vbscript:` must not survive into generated Markdown links/images
- C0 / DEL control-character bypasses must remain rejected
- rejection must degrade safely:
  - unsafe link → visible link text only
  - unsafe image → alt text only
  - do not emit `[text]()` or `![]()`
- titles are text metadata, not navigation targets; do not over-sanitize unrelated attributes unless necessary

## Architecture boundary

Do not solve this by routing legacy `html_to_markdown()` through the DOM.

Keep the #37 scaffold intact:

```
html_to_markdown()
  -> _html_to_markdown_impl()
     -> _HTMLToMarkdownParser
```

Apply the shared safety boundary inside the legacy parser where `href` / `src` are consumed.

The internal engine remains DOM-agnostic.

## Tests

Extend the converter integration scaffold so the current
`unsafe_link_sanitization` known gap moves from KNOWN_DOM_LEGACY_GAPS into
ordinary parity coverage.

Add explicit cases for:

- `javascript:`
- mixed-case `JavaScript:`
- `javascript\x00:`
- tab / newline control-character variants where the parser accepts the attribute
- `data:`
- `vbscript:`
- safe `https:`
- safe `mailto:`
- relative URLs
- image `src` rejection and alt-text degrade
- no empty link/image target syntax

The test should prove **final Markdown parity**, not merely intermediate DOM/HTML parity.

## Non-goals

Do not include:

- DOM-first conversion
- nested-list fixes
- whitespace normalization
- table structural tag expansion
- reference-style Markdown link rendering
- full HTML5 / CommonMark behavior
- unrelated sanitizer expansion

## Exit criteria

- the `unsafe_link_sanitization` entry can be removed from known-gap baseline
- parity cases cover the safe/unsafe URL contract
- existing public `html_to_markdown()` behavior changes only for unsafe URL targets
- existing safe URL fixtures remain unchanged
- CI green
- Claude / GPT review finds no Blocking issues

## Routing

from: gpt
to: @cursoragent @claude

Cursor: implementation lane.
Claude: review / contract audit.
GPT: architecture and final pre-merge review.
