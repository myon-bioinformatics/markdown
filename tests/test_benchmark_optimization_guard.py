"""Fault-injection checks do not require a historical git checkout."""
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]


class BenchmarkGuardTests(unittest.TestCase):
    def test_scanner_and_toc_mismatches_stop_optimized_execution(self):
        for attribute, replacement, diagnostic in (
            ('_scan_lines', 'lambda lines: []', 'scanner field mismatch'),
            ('table_of_contents', 'lambda content: object()', 'table of contents mismatch'),
        ):
            code = f'''
import runpy, sys, types, markdown
reference = types.ModuleType('guard_reference')
reference._scan_lines = markdown._scan_lines
reference.table_of_contents = markdown.table_of_contents
sys.modules['guard_reference'] = reference
ns = runpy.run_path('scripts/benchmark_scanned_lines.py')['main'].__globals__
ns['subprocess'].check_output = lambda *a, **kw: b'from guard_reference import _scan_lines, table_of_contents'
markdown.{attribute} = {replacement}
ns['main']()
'''
            with self.subTest(attribute=attribute):
                result = subprocess.run([sys.executable, '-O', '-S', '-c', code],
                                        cwd=ROOT, capture_output=True, text=True, timeout=30)
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertIn(diagnostic, result.stderr)
                self.assertEqual(result.stdout, '')
