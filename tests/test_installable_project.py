"""The repository root must stay installable by ``uv pip install`` of the git URL.

The parent vendor driver treats a missing build backend, ``tool.uv.package = false``,
or any third-party runtime dependency as a skip. ``markdown.py`` itself stays a
stdlib-only file so a standalone copy still imports under ``python -S``.
"""
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_root_project_is_uv_installable_without_runtime_deps():
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = data["project"]
    assert project["name"] == "md-market"
    assert project["requires-python"] == ">=3.11"
    assert project["dependencies"] == []
    assert data["build-system"]["build-backend"] == "hatchling.build"
    requires = data["build-system"]["requires"]
    assert requires and all(">=" in item and "==" not in item for item in requires)
    uv_tool = data.get("tool", {}).get("uv", {})
    assert uv_tool.get("package") is not False
    wheel = data["tool"]["hatch"]["build"]["targets"]["wheel"]
    assert wheel["only-include"] == ["markdown.py"]


def test_standalone_copy_imports_under_python_s(tmp_path):
    import os
    import subprocess
    import sys

    destination = tmp_path / "markdown.py"
    destination.write_bytes((ROOT / "markdown.py").read_bytes())
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    completed = subprocess.run(
        [sys.executable, "-S", "-c", "import markdown; print(markdown.make_link('A', 'https://example.com'))"],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "[A](https://example.com)"
