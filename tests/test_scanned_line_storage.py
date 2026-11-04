from pathlib import Path
import copy
import pickle
import sys
import unittest
from dataclasses import FrozenInstanceError
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import markdown as md


class ScannedLineStorageTests(unittest.TestCase):
    def test_scan_context_and_storage_roundtrip(self):
        lines=['hello','```py','code','```','~~~','more','~~~']
        result=md._scan_lines(lines)
        self.assertEqual([r.text for r in result],lines)
        self.assertEqual([r.in_fenced_code for r in result],[False,True,True,True,True,True,True])
        self.assertEqual([r.is_fence_open for r in result],[False,True,False,False,True,False,False])
        self.assertEqual([r.is_fence_close for r in result],[False,False,False,True,False,False,True])
        for row in result:
            self.assertEqual(pickle.loads(pickle.dumps(row)),row)
            self.assertEqual(copy.copy(row),row)
            self.assertFalse(hasattr(row,'__dict__'))
            with self.assertRaises(FrozenInstanceError):row.text='changed'


if __name__=='__main__':unittest.main()
