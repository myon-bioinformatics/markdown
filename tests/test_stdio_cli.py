import json
from pathlib import Path
import subprocess
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]

class StdioCli(unittest.TestCase):
 def run_cli(self,*args,input=''):
  return subprocess.run([sys.executable,'-S',ROOT/'markdown.py',*args],input=input,text=True,capture_output=True,timeout=10)
 def test_inventory_and_help(self):
  self.assertEqual(self.run_cli('--help').returncode,0)
  json.loads(self.run_cli().stdout)
 def test_transform_stdin_and_missing_input(self):
  result=self.run_cli('to-html',input='# Hello\n')
  self.assertEqual(result.returncode,0,result.stderr)
  self.assertIn('<h1',result.stdout)
  self.assertIn('Hello',result.stdout)
  self.assertEqual(self.run_cli('to-html','/path/that/does/not/exist').returncode,2)
 def test_invalid_operation(self):
  result=self.run_cli('invalid')
  self.assertEqual(result.returncode,2)
  self.assertNotIn('Traceback',result.stderr)
if __name__=='__main__':unittest.main()
