"""Offline contracts for dependency slices and fail-closed frontend evidence."""
import ast
import importlib.util
from pathlib import Path
import tempfile
import tomllib
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('check_frontend_slice', ROOT / 'scripts/check_frontend_slice.py')
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


class FrontendNanoTests(unittest.TestCase):
    def test_groups_preserve_existing_frontend_roots(self):
        project = tomllib.loads((ROOT / 'pyproject.toml').read_text())
        groups = project['dependency-groups']
        self.assertEqual(groups['frontend-gradio'], ['gradio>=6.30.0'])
        self.assertEqual(groups['frontend-streamlit'], ['streamlit>=1.66.0'])
        self.assertEqual(groups['frontend-browser'], ['playwright>=1.64.0'])
        self.assertEqual(groups['frontend'], [
            {'include-group': 'frontend-gradio'},
            {'include-group': 'frontend-streamlit'},
            {'include-group': 'frontend-browser'},
        ])
        lock = tomllib.loads((ROOT / 'uv.lock').read_text())
        package = next(p for p in lock['package'] if p['name'] == 'md-market')
        self.assertEqual(package['dev-dependencies']['frontend'], [
            {'name': 'gradio'}, {'name': 'playwright'}, {'name': 'streamlit'}])
        for name in ('gradio', 'streamlit', 'browser'):
            root = 'playwright' if name == 'browser' else name
            self.assertEqual(package['dev-dependencies'][f'frontend-{name}'], [{'name': root}])

    def test_expected_identities_cover_every_existing_slice_test(self):
        actual = set()
        for frontend in checker.EXPECTED:
            for suffix in ('curl', 'ui'):
                path = ROOT / f'tests/frontend/test_{frontend}_{suffix}.py'
                tree = ast.parse(path.read_text())
                actual.update((f'tests.frontend.{path.stem}', node.name)
                              for node in tree.body
                              if isinstance(node, ast.FunctionDef) and node.name.startswith('test_'))
        expected = set.union(*checker.EXPECTED.values())
        self.assertEqual(actual, expected)
        self.assertEqual(len(expected), 7)

    def test_workflow_keeps_two_independent_no_browser_slices(self):
        workflow = (ROOT / '.github/workflows/ci.yml').read_text()
        block = workflow.split('  frontend-mock-pytest-latest:', 1)[1].split('  frontend-smoke:', 1)[0]
        self.assertIn('frontend: [gradio, streamlit]', block)
        self.assertIn('fail-fast: false', block)
        self.assertIn('--group "frontend-${{ matrix.frontend }}"', block)
        self.assertIn('uv run --no-sync pytest -q', block)
        self.assertIn('scripts/check_frontend_slice.py ${{ matrix.frontend }}', block)
        self.assertIn('if-no-files-found: error', block)
        self.assertNotIn('playwright install', block)
        self.assertNotIn('--group frontend ', block)
        self.assertIn('find_spec("playwright") is None', block)
        smoke = workflow.split('  frontend-smoke:', 1)[1].split('  failure-identity:', 1)[0]
        self.assertIn("github.event_name == 'workflow_dispatch'", smoke)
        self.assertIn('--group frontend ', smoke)
        self.assertIn('playwright install --with-deps --only-shell chromium', smoke)

    def test_complete_reports_and_rejection_probes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'junit.xml'
            for frontend, identities in checker.EXPECTED.items():
                for mutation in ('good', 'missing', 'duplicate', 'renamed', 'skipped', 'failure', 'error'):
                    with self.subTest(frontend=frontend, mutation=mutation):
                        root = ET.Element('testsuites')
                        suite = ET.SubElement(root, 'testsuite')
                        for classname, name in sorted(identities):
                            ET.SubElement(suite, 'testcase', classname=classname, name=name)
                        case = suite[0]
                        if mutation == 'missing':
                            suite.remove(case)
                        elif mutation == 'duplicate':
                            ET.SubElement(suite, 'testcase', **case.attrib)
                        elif mutation == 'renamed':
                            case.set('name', 'unexpected')
                        elif mutation in ('skipped', 'failure', 'error'):
                            ET.SubElement(case, mutation)
                        ET.ElementTree(root).write(path)
                        if mutation == 'good':
                            checker.check(frontend, path)
                        else:
                            with self.assertRaises(ValueError):
                                checker.check(frontend, path)


if __name__ == '__main__':
    unittest.main()
