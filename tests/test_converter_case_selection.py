"""Case selection happens before conversion and preserves evaluation scope."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize('name', ['converter_parity_report', 'converter_contract_audit'])
def test_list_never_reads_fixtures_or_converts(name, monkeypatch, capsys):
    module = load(name)
    def forbidden(*args, **kwargs):
        raise AssertionError('list must not read or convert')
    monkeypatch.setattr(Path, 'read_text', forbidden)
    monkeypatch.setattr(module.md, 'html_to_markdown', forbidden)
    assert module.main(['--case', 'html:basic*', '--list']) == 0
    assert json.loads(capsys.readouterr().out) == {'cases': ['html:basic_blocks']}


@pytest.mark.parametrize('name', ['converter_parity_report', 'converter_contract_audit'])
def test_subset_is_explicit_and_preserves_per_case_results(name):
    module = load(name)
    whole = module.collect_report()
    subset = module.collect_report(patterns=('html:basic*', 'html:basic*', 'html:table'), exclude=('table',))
    expected = [c for c in whole['cases'] if c['id'] == 'basic_blocks']
    if name.endswith('audit'):
        expected = [c for c in expected if c['kind'] == 'html']
    assert subset['cases'] == expected
    assert subset['case_count'] == 1 and subset['selection']['scope'] == 'selected_cases'
    assert subset['selection']['selected'] == 1
    assert 'selection' not in whole
    if name.endswith('report'):
        assert subset['decision_hint'] == 'selected_cases_only'


def test_excluded_markdown_and_cycles_are_not_converted(monkeypatch):
    module = load('converter_contract_audit')
    def forbidden(*args, **kwargs):
        raise AssertionError('excluded converters must not run')
    monkeypatch.setattr(module, '_markdown_record', forbidden)
    monkeypatch.setattr(module, '_structured_cycle_record', forbidden)
    result = module.collect_report(patterns=('html:basic_blocks',))
    assert result['case_count'] == 1 and result['structured_cycle_count'] == 0


@pytest.mark.parametrize('name', ['converter_parity_report', 'converter_contract_audit'])
def test_invalid_empty_or_mixed_modes_never_write(tmp_path, name):
    out = tmp_path / 'result.json'
    script = ROOT / 'scripts' / (name + '.py')
    for options in (['--case', 'missing'], ['--case', ''], ['--list']):
        result = subprocess.run([sys.executable, '-S', str(script), '--out', str(out)] + options,
                                cwd=tmp_path, capture_output=True, text=True)
        assert result.returncode == 2 and result.stdout == ''
        assert not out.exists()
    result = subprocess.run([sys.executable, '-S', str(script), '--case', 'html:basic_blocks', '--list'],
                            cwd=tmp_path, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)['cases'] == ['html:basic_blocks']
