"""Keep the stdlib runtime floor separate from the pytest environment."""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_runtime_floor_has_a_supported_runner_without_skipping_behavior():
    workflow = yaml.safe_load((ROOT / '.github/workflows/runtime-compatibility.yml').read_text())
    job = workflow['jobs']['runtime']
    assert job['runs-on'] == "${{ matrix.python == '3.9' && 'ubuntu-24.04' || 'ubuntu-latest' }}"
    assert job['strategy']['matrix'] == {'python': ['3.9', '3.10', '3.11', '3.12', '3.13', '3.14']}
    assert job['strategy']['fail-fast'] is False
    assert 'if' not in job and not job.get('continue-on-error', False)
    behavior = [step for step in job['steps'] if 'run' in step]
    assert len(behavior) == 1
    assert behavior[0]['run'] == 'python -S -m unittest discover -s tests -p test_runtime_compatibility.py -v'
    assert 'if' not in behavior[0] and not behavior[0].get('continue-on-error', False)
    ci = yaml.safe_load((ROOT / '.github/workflows/ci.yml').read_text())
    assert ci['jobs']['pytest']['strategy']['matrix']['python-version'] == ['3.11', '3.12', '3.13', '3.14']
