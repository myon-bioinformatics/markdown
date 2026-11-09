"""Keep dependency-free runtime coverage aligned with the supported Python floor."""
from pathlib import Path
import tomllib

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_runtime_floor_runs_on_the_default_runner_without_skipping_behavior():
    workflow = yaml.safe_load((ROOT / '.github/workflows/runtime-compatibility.yml').read_text())
    job = workflow['jobs']['runtime']
    assert job['runs-on'] == 'ubuntu-latest'
    assert job['strategy']['matrix'] == {'python': ['3.11', '3.12', '3.13', '3.14']}
    assert job['strategy']['fail-fast'] is False
    assert 'if' not in job and not job.get('continue-on-error', False)
    behavior = [step for step in job['steps'] if 'run' in step]
    assert len(behavior) == 1
    assert behavior[0]['run'] == 'python -S -m unittest discover -s tests -p test_runtime_compatibility.py -v'
    assert 'if' not in behavior[0] and not behavior[0].get('continue-on-error', False)
    ci = yaml.safe_load((ROOT / '.github/workflows/ci.yml').read_text())
    assert ci['jobs']['test']['strategy']['matrix']['python-version'] == ['3.11', '3.12', '3.13', '3.14']


def test_source_runtime_floor_matches_packaged_runtime_and_documentation():
    project = tomllib.loads((ROOT / 'pyproject.toml').read_text(encoding='utf-8'))
    assert project['project']['requires-python'] == '>=3.11'
    readme = (ROOT / 'README.md').read_text(encoding='utf-8')
    assert 'source runtime requires Python 3.11 or newer' in readme
    assert 'Python 3.9 and 3.10 are no longer supported.' in readme
    discovery = (ROOT / 'docs/unittest-discovery.md').read_text(encoding='utf-8')
    assert 'Run from this repository root with Python 3.11 or newer.' in discovery
