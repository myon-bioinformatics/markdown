"""toml_to_markdown without tomllib: Node + smol-toml must give the same document."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from typing import Union

import pytest

import markdown as md

# Registered fake NODE paths: vendored ``_probe_node_once`` / ``Popen`` see these via
# stubbed ``subprocess.run`` (--version) and ``subprocess.Popen`` (-e) in node_launch.
_FAKE_NODE_SPECS: dict[str, tuple[str, str]] = {}


def _fake_node_key(path: Union[Path, str]) -> str:
    return str(Path(path).resolve())


def _run_fake_on_eval(on_eval: str) -> tuple[bytes, bytes, int]:
    import sys
    from io import StringIO

    stderr = StringIO()
    old_stderr = sys.stderr
    code = 0
    try:
        sys.stderr = stderr
        exec(on_eval, {"sys": sys})  # noqa: S102
    except SystemExit as exc:
        if exc.code is None:
            code = 0
        elif isinstance(exc.code, int):
            code = exc.code
        else:
            code = 1
    finally:
        sys.stderr = old_stderr
    return b"", stderr.getvalue().encode("utf-8", errors="replace"), code


class _FakeNodePopen:
    """Minimal ``Popen`` stand-in for registered fake node executables."""

    def __init__(self, command: list[str], on_eval: str, **_kwargs: object) -> None:
        self.args = command
        self._on_eval = on_eval
        stdin_r, stdin_w = os.pipe()
        stdout_r, stdout_w = os.pipe()
        stderr_r, stderr_w = os.pipe()
        self.stdin = os.fdopen(stdin_w, "wb")
        self.stdout = os.fdopen(stdout_r, "rb")
        self.stderr = os.fdopen(stderr_r, "rb")
        self._stdin_r = stdin_r
        self._stdout_w = stdout_w
        self._stderr_w = stderr_w
        self.returncode: int | None = None
        self._done = threading.Event()

        def worker() -> None:
            # Drain stdin in the background so ``wait()`` is not blocked on EOF
            # before ``node_launch``'s stdin writer thread runs.
            def drain_stdin() -> None:
                try:
                    with os.fdopen(self._stdin_r, "rb") as stream:
                        while stream.read(65536):
                            pass
                except OSError:
                    pass

            threading.Thread(target=drain_stdin, daemon=True).start()
            stdout, stderr, rc = _run_fake_on_eval(self._on_eval)
            try:
                if stdout:
                    os.write(self._stdout_w, stdout)
                if stderr:
                    os.write(self._stderr_w, stderr)
            finally:
                os.close(self._stdout_w)
                os.close(self._stderr_w)
                self.returncode = rc
                self._done.set()

        threading.Thread(target=worker, daemon=True).start()

    def wait(self, timeout: float | None = None) -> int:
        if not self._done.wait(timeout):
            raise subprocess.TimeoutExpired(self.args, timeout)
        return self.returncode if self.returncode is not None else -1

    def kill(self) -> None:
        self.returncode = -9
        self._done.set()


@pytest.fixture(autouse=True)
def _node_launch_process_layer_stub(monkeypatch):
    """Stub ``node_launch``'s ``subprocess`` calls for registered fake node paths only."""
    node_launch = md._node_launch_module()
    real_run = node_launch.subprocess.run
    real_popen = node_launch.subprocess.Popen

    def fake_run(args, *pargs, **kwargs):
        if args and not isinstance(args, (str, bytes)):
            argv = list(args)
        else:
            argv = [args, *pargs]
        spec = _FAKE_NODE_SPECS.get(_fake_node_key(argv[0])) if argv else None
        if spec is not None and len(argv) >= 2 and argv[1] == "--version":
            version, _ = spec
            return subprocess.CompletedProcess(
                tuple(argv), 0, (version + "\n").encode(), b""
            )
        return real_run(args, *pargs, **kwargs)

    def fake_popen(command, **kwargs):
        argv = [os.fspath(part) for part in command]
        spec = _FAKE_NODE_SPECS.get(_fake_node_key(argv[0])) if argv else None
        if spec is None:
            return real_popen(command, **kwargs)
        _, on_eval = spec
        return _FakeNodePopen(argv, on_eval, **kwargs)

    monkeypatch.setattr(node_launch.subprocess, "run", fake_run)
    monkeypatch.setattr(node_launch.subprocess, "Popen", fake_popen)
    yield
    _FAKE_NODE_SPECS.clear()


MODULES = Path(__file__).resolve().parent / "mirror" / "node_modules"
needs_node = pytest.mark.skipif(shutil.which("node") is None or not (MODULES / "smol-toml").is_dir(),
                                reason="run `npm ci --prefix tests/mirror` to enable the Node TOML reader")
SOURCE = ('title = "TOML Example"\nenabled = true\nratio = 1.25\nports = [8000, 8001]\nbig = 9007199254740993\n'
          '[owner]\nname = "妙本"\n[database]\ndata = [["delta", "phi"], [3.14]]\n'
          '[[products]]\nname = "Hammer"\nsku = 738594937\n')


@pytest.fixture()
def node_only(monkeypatch):
    monkeypatch.setenv("NODE_PATH", str(MODULES))
    monkeypatch.setattr(md, "tomllib", None)
    monkeypatch.setattr(md, "_TOML_READER", [])
    md._node_launch_module().clear_probe_cache()
    yield


def _write_fake_node(tmp_path: Path, *, version: str, on_eval: str) -> Path:
    """Register a fake NODE path; process-layer stubs implement ``--version`` and ``-e``."""
    name = "fake_node.exe" if os.name == "nt" else "fake_node"
    dest = tmp_path / name
    dest.write_bytes(b"")
    _FAKE_NODE_SPECS[_fake_node_key(dest)] = (version, on_eval)
    return dest


def _use_fake_node(monkeypatch, script: Union[Path, str]) -> None:
    monkeypatch.setattr(md, "tomllib", None)
    monkeypatch.setattr(md, "_TOML_READER", [])
    monkeypatch.setenv("NODE", str(script))
    md._node_launch_module().clear_probe_cache()


@needs_node
def test_node_reader_matches_tomllib(node_only):
    assert md.toml_reader() == "node"
    document = md.toml_to_markdown(SOURCE)
    assert md.markdown_to_structured(document)["big"] == 9007199254740993
    if sys.version_info >= (3, 11):
        import tomllib
        assert md.markdown_to_structured(document) == tomllib.loads(SOURCE)


@needs_node
@pytest.mark.parametrize("source,expected", [
    ("values = [9007199254740991, 9007199254740992, 9007199254740993, "
     "-9007199254740993, 9223372036854775807, -9223372036854775808]\n",
     {"values": [9007199254740991, 9007199254740992, 9007199254740993,
                 -9007199254740993, 9223372036854775807, -9223372036854775808]}),
    ("values = [1.0, -0.0, 1e3, 9007199254740992.0, 5e-324]\n",
     {"values": [1.0, -0.0, 1000.0, 9007199254740992.0, 5e-324]}),
    ('x = {"\\u0000int" = "42"}\n', {"x": {"\u0000int": "42"}}),
    ('x = {"\\u0000int" = "not an integer"}\n', {"x": {"\u0000int": "not an integer"}}),
    ('[[items]]\nvalue = 9007199254740993\nratio = 1.0\n'
     '[items.nested]\n"\\u0000int" = "42"\n',
     {"items": [{"value": 9007199254740993, "ratio": 1.0, "nested": {"\u0000int": "42"}}]}),
])
def test_node_reader_preserves_numeric_types_and_literal_keys(node_only, source, expected):
    document = md.toml_to_markdown(source)
    # Canonical documents distinguish int/float and the sign of zero, unlike ==.
    assert document == md.structured_to_markdown(expected, title="TOML")
    if sys.version_info >= (3, 11):
        import tomllib
        assert document == md.structured_to_markdown(tomllib.loads(source), title="TOML")


@needs_node
def test_node_reader_keeps_the_reversible_subset_and_errors(node_only):
    with pytest.raises(ValueError, match="outside the reversible structured subset"):
        md.toml_to_markdown("when = 1979-05-27\n")
    with pytest.raises(ValueError, match="outside the reversible structured subset"):
        md.toml_to_markdown("x = inf\n")
    with pytest.raises(ValueError, match="Invalid TOML"):
        md.toml_to_markdown("a = \n")


def test_no_reader_names_both_options(monkeypatch):
    monkeypatch.setattr(md, "tomllib", None)
    monkeypatch.setattr(md, "_TOML_READER", [])
    monkeypatch.setattr(shutil, "which", lambda name, **kw: None)
    md._node_launch_module().clear_probe_cache()
    assert md.toml_reader() is None
    with pytest.raises(RuntimeError, match=r"tomllib.*Node 24\+.*smol-toml"):
        md.toml_to_markdown("a = 1\n")


def test_node_20_is_rejected_as_reader(tmp_path, monkeypatch):
    script = _write_fake_node(tmp_path, version="v20.0.0", on_eval="pass")
    _use_fake_node(monkeypatch, script)
    node_launch = md._node_launch_module()
    with pytest.raises(node_launch.NodeNotFoundError, match=r"must be 24.*found 20"):
        node_launch.resolve_node(env_var="NODE")
    assert md.toml_reader() is None
    with pytest.raises(RuntimeError, match=r"Node 24\+.*smol-toml"):
        md.toml_to_markdown("a = 1\n")


def test_toml_reader_probe_timeout_reraises_timeout_expired(monkeypatch):
    monkeypatch.setattr(md, "tomllib", None)
    monkeypatch.setattr(md, "_TOML_READER", [])
    node_launch = md._node_launch_module()
    monkeypatch.setattr(node_launch, "resolve_node", lambda **kwargs: "/fake/node")

    def timed_out(*args, **kwargs):
        raise node_launch.LaunchError(
            "node_launch: Node process timed out",
            code="ELAUNCHFAILURE",
            stdout=b"",
            stderr=b"",
        )

    monkeypatch.setattr(node_launch, "run", timed_out)
    with pytest.raises(subprocess.TimeoutExpired) as info:
        md.toml_reader()
    assert info.value.timeout == 30
    assert info.value.cmd == ["/fake/node", "-e", "require('smol-toml')"]


def test_toml_node_run_timeout_cmd_includes_resolved_node(monkeypatch):
    node_launch = md._node_launch_module()
    fake = "/opt/node24/bin/node"
    monkeypatch.setattr(node_launch, "resolve_node", lambda **kwargs: fake)

    def timed_out(*args, **kwargs):
        raise node_launch.LaunchError(
            "node_launch: Node process timed out",
            code="ELAUNCHFAILURE",
            stdout=b"",
            stderr=b"",
        )

    monkeypatch.setattr(node_launch, "run", timed_out)
    with pytest.raises(subprocess.TimeoutExpired) as info:
        md._toml_node_run("-e", "1+1", timeout=12, check=False)
    assert info.value.timeout == 12
    assert info.value.cmd == [fake, "-e", "1+1"]


def test_toml_node_run_pops_node_and_probe_before_calling_run(monkeypatch):
    node_launch = md._node_launch_module()
    resolved = "/resolved/node"
    monkeypatch.setattr(node_launch, "resolve_node", lambda **kwargs: resolved)
    seen: dict[str, object] = {}

    def record_run(*args, **kwargs):
        seen["kwargs"] = dict(kwargs)
        return subprocess.CompletedProcess([resolved, "-e", "x"], 0, b"", b"")

    monkeypatch.setattr(node_launch, "run", record_run)
    md._toml_node_run("-e", "x", node="/explicit", probe=True, check=False)
    assert seen["kwargs"]["node"] == resolved
    assert seen["kwargs"]["probe"] is False


def test_toml_loads_timeout_reraises_timeout_expired(monkeypatch):
    monkeypatch.setattr(md, "tomllib", None)
    monkeypatch.setattr(md, "_TOML_READER", ["node"])
    node_launch = md._node_launch_module()
    monkeypatch.setattr(node_launch, "resolve_node", lambda **kwargs: "/fake/node")

    def timed_out(*args, **kwargs):
        raise node_launch.LaunchError(
            "node_launch: Node process timed out",
            code="ELAUNCHFAILURE",
            stdout=b"",
            stderr=b"",
        )

    monkeypatch.setattr(node_launch, "run", timed_out)
    with pytest.raises(subprocess.TimeoutExpired) as info:
        md.toml_to_markdown("a = 1\n")
    assert info.value.timeout == 30
    assert info.value.cmd == ["/fake/node", "-e", md._TOML_NODE_SCRIPT]


def test_toml_loads_stdin_closed_nonzero_surfaces_stderr(tmp_path, monkeypatch):
    """Non-zero exit with stderr after stdin close (via fake NODE process stub)."""
    script = _write_fake_node(
        tmp_path,
        version="v24.0.0",
        on_eval='import sys; sys.stderr.write("boom\\n"); sys.exit(3)',
    )
    _use_fake_node(monkeypatch, script)
    monkeypatch.setattr(md, "_TOML_READER", ["node"])
    with pytest.raises(RuntimeError, match=r"Node TOML reader failed: boom"):
        md.toml_to_markdown("a = 1\n")
