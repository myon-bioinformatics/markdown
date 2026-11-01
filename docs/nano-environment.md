# Opt-in nano environment: the real Gradio frontend

The `markdown.py` conversion core already uses only the standard library; leave
that core alone. This recipe isolates the **existing Gradio text-input API** from
the separate Streamlit and Playwright frontend dependencies. It does not replace
Gradio, NumPy, Pandas, Pillow, or their native dependencies.

This is an opt-in installation recipe, not a new default environment. Dependency
groups, locks, application code, all independent tests, browser lanes, and CI/Pages
settings are unchanged. No Docker is needed for this selected API feature;
Docker-based integration and browser tests remain separate, valid environments.

## Reviewed pins and prerequisites

- Shared preparation tool: parent PR [#195](https://github.com/myon-bioinformatics/myon-bioinformatics/pull/195),
  actual merge commit `3128b4019b9949a6ccc80c686cd84c93f04af119`.
- Child source: `f04d233d2edc63650439fbb7692434e9f2c66266`. The recipe downloads
  five exact source/license/manifest files into scratch, not your current checkout.
- Existing trusted **CPython 3.12**, **uv** (measured with 0.13.4), and a POSIX shell.
  The preparer requires Python 3.11+, but this recipe deliberately uses the tested
  3.12 lane. It never downloads Python. Native wheels must exist for your OS/ABI;
  the measured host was Linux x86_64. Windows/other ABI parity is not established.

Do not replace the pins with `main` or remove hash checks when a source changes.
Review a new snapshot separately. The helper verifies only the manifest/lock
blobs; the download step below additionally verifies the exact application files
used by this example. It does not claim to verify an entire checkout or ancestry.

## 1. Fetch and verify, then prepare without installing

Run the following blocks in the **same shell**. The first block fetches only
immutable GitHub source text. No downloaded code runs until every hash matches.
It creates a fresh private directory outside your checkout. Failed fetches stop
the block; discard that scratch directory rather than using partial outputs.

```sh
set -eu
umask 077
PYTHON=$(python3 -S -c 'import sys; assert sys.version_info[:2] == (3, 12), "use an existing Python 3.12"; print(sys.executable)')
UV=$("$PYTHON" -S -c 'import pathlib, shutil; p = shutil.which("uv"); assert p, "install/provide trusted uv separately"; print(pathlib.Path(p).resolve())')
WORK=$(mktemp -d "${TMPDIR:-/tmp}/markdown-gradio-XXXXXXXX")
WORK=$("$PYTHON" -S -c 'from pathlib import Path; import sys; print(Path(sys.argv[1]).resolve())' "$WORK")
export WORK
mkdir -p "$WORK/prepared" "$WORK/home" "$WORK/tmp" "$WORK/cache" "$WORK/config"
"$PYTHON" -S - "$WORK" <<'PY'
import hashlib
from pathlib import Path
import sys
import urllib.request

root = Path(sys.argv[1])
parent = "https://raw.githubusercontent.com/myon-bioinformatics/myon-bioinformatics/3128b4019b9949a6ccc80c686cd84c93f04af119/"
child = "https://raw.githubusercontent.com/myon-bioinformatics/markdown/f04d233d2edc63650439fbb7692434e9f2c66266/"
files = [
    (parent, "tools/nano_export.py", "parent/tools/nano_export.py", "aa74cde16da7a33c4cc1398f78c4d0447179ea752d262e8592a11ddb8ce8c3e8"),
    (parent, "docs/stdlib-shrink-queue.json", "parent/docs/stdlib-shrink-queue.json", "6b71651b3f361bc54bd921b557d3fc347bbd13e0b98035896c7fa11f2190e535"),
    (child, "pyproject.toml", "source/pyproject.toml", "9f8b4ae84e7b6a27b1c6c661962a9e87285fd4eac7ba92fc4dd4eef23a39d505"),
    (child, "uv.lock", "source/uv.lock", "622c556235a6bdbc37135a7f536995742a107db20439963bf88d86ada5bad720"),
    (child, "markdown.py", "source/markdown.py", "56e41cac2e1708b9ffc2c85ed62eac7ec9dd500b48a4c3687dfab13479e0ba7b"),
    (child, "demos/gradio_app.py", "source/demos/gradio_app.py", "25d6d78ec8e7ad73b97d1ae19e2b96ea241d8aadd82f0e854fc9298bbb10618c"),
    (child, "LICENSE", "source/LICENSE", "15f66204c4a6a1ce0c94f0ed4319ff9400f872e85fd32c95f21695c2f231af59"),
]
verified = []
for base, source, destination, digest in files:
    with urllib.request.urlopen(base + source, timeout=30) as response:
        data = response.read(2 * 1024 * 1024 + 1)
    if len(data) > 2 * 1024 * 1024 or hashlib.sha256(data).hexdigest() != digest:
        raise SystemExit("source hash/size mismatch: " + source)
    verified.append((root / destination, data))
for path, data in verified:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
print("Verified all seven pinned files; no packages installed.")
PY
"$PYTHON" -S "$WORK/parent/tools/nano_export.py" \
  --feature markdown-gradio --source "$WORK/source" \
  --output-parent "$WORK/prepared" --uv "$UV" > "$WORK/prepared.json"
FEATURE=$("$PYTHON" -S - "$WORK" <<'PY'
import hashlib
import json
from pathlib import Path
import sys
root = Path(sys.argv[1]).resolve()
directory = Path(json.loads((root / "prepared.json").read_text())["directory"]).resolve()
assert directory.parent == root / "prepared"
receipt = json.loads((directory / "receipt.json").read_text())
assert receipt["recipe"] == "markdown-gradio"
assert receipt["inventory_source_commit"] == "f04d233d2edc63650439fbb7692434e9f2c66266"
assert receipt["exported_requirement_rows"] == 56
assert hashlib.sha256((directory / "requirements.txt").read_bytes()).hexdigest() == receipt["requirements_sha256"]
print(directory)
PY
)
printf 'Prepared requirements and receipt: %s\n' "$FEATURE"
```

The official uv operation is locked/offline, selects the existing `frontend`
group, excludes default dev groups and the project, and prunes only Streamlit
and Playwright. The **56 requirement rows are not 56 installed packages**:
they contain platform markers and two mutually exclusive NumPy versions.
Preparation starts no server, installs nothing, and does not run tests.

## 2. Explicit package installation (optional network step)

Only continue if you want to install this feature. These commands download the
existing locked wheels from official PyPI into a fresh private cache/venv; they
do not upgrade the repository's dependencies or install all dev groups. Source
builds are prohibited. Missing wheels/network failures stop rather than falling
back to unpinned packages. The cleared environment intentionally does not inherit
custom registries, credentials, or proxy settings.

```sh
env -i PATH="$PATH" HOME="$WORK/home" TMPDIR="$WORK/tmp" \
  XDG_CONFIG_HOME="$WORK/config" UV_PYTHON_DOWNLOADS=never \
  "$UV" --no-config venv --python "$PYTHON" --no-python-downloads "$WORK/venv"
env -i PATH="$PATH" HOME="$WORK/home" TMPDIR="$WORK/tmp" \
  XDG_CONFIG_HOME="$WORK/config" UV_PYTHON_DOWNLOADS=never \
  "$UV" --no-config pip install --python "$WORK/venv/bin/python" \
  --default-index https://pypi.org/simple --require-hashes --only-binary :all: \
  --no-deps --link-mode copy --cache-dir "$WORK/cache" \
  -r "$FEATURE/requirements.txt"
```

Keep the source, requirements and receipt together. The venv contains neither
the local `markdown.py` project nor the full test tools. Use the staged source
directory below; do not accidentally import an unrelated installed `markdown`.

## 3. Use the unchanged local app (explicit opt-in)

This starts a loopback-only Gradio server, **not a browser**, share tunnel,
external API, model, or Docker container. Stop with Ctrl-C. Choose another unused
port for another worker. Each worker should repeat the private-workdir recipe
or provide separate HOME/tmp/cache/output paths; this is dependency/output
separation, not container security isolation or CPU/RAM quotas.

```sh
(
  cd "$WORK/source"
  env -i PATH="$PATH" HOME="$WORK/home" TMPDIR="$WORK/tmp" \
    XDG_CONFIG_HOME="$WORK/config" XDG_CACHE_HOME="$WORK/cache" \
    GRADIO_ANALYTICS_ENABLED=False HF_HUB_DISABLE_TELEMETRY=1 HF_HUB_OFFLINE=1 \
    "$WORK/venv/bin/python" - <<'PY'
from demos.gradio_app import build_app
demo = build_app()
demo.launch(server_name="127.0.0.1", server_port=7860, share=False, inbrowser=False)
PY
)
```

The environment flags disable documented analytics/HF online behavior, but this
short usage example is **not an egress sandbox**. The measured acceptance harness
additionally enforced loopback/subprocess audit checks. If making client calls,
use `gradio_client.Client("http://127.0.0.1:7860", analytics_enabled=False)`;
do not rely solely on the Gradio environment flag for client analytics.

The public API is `/analyze`: text plus `None` for the upload argument returns
headings, links, images and inventory JSON. This recipe's acceptance evidence is
for text input only; file uploads, all widgets, browser appearance and Streamlit
parity were not established.

## Evidence and limits

The [parent report and reproducible evidence](https://github.com/myon-bioinformatics/myon-bioinformatics/blob/3128b4019b9949a6ccc80c686cd84c93f04af119/docs/nano-gradio-environment.md)
record one completed matched installation pair: **72→52 installed distributions**,
**642,781,043→239,130,663 venv apparent regular-file bytes**. The next feature
install timed out fetching a NumPy wheel; the series stopped (planned 6,
attempted 3, completed 2, failed 1, unstarted 3). There is no three-sample install
median or general speed claim. Runtime/stdlib/source/cache are excluded from
those venv bytes.

Using the completed pair, 24 API workers produced 144 matching complete responses;
the four unchanged original API tests ran in both profiles (8 executions, 0 skips).
Both profiles already supported parallel jobs. This is not full-suite, upload,
visual, cross-platform, or build-speed proof. The full existing test/frontend
environments remain available and unchanged; this small venv is not a substitute
for their independent coverage. This documentation adoption does not rerun the
benchmark, change CI, or claim the whole repository is minimized.
