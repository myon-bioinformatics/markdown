# Slotted internal scanner records

The private frozen `_ScannedLine` record now uses dataclass slots. Its four fields,
field defaults, equality and immutability remain unchanged; per-instance attribute
dictionaries are removed. No dependencies or public API changes. Code relying on
the private record's `__dict__` would need adaptation.

The source runtime now requires Python 3.11 or newer, matching the installable
project. Python 3.9 and 3.10 are no longer supported; the dependency-free CI lane
continues to run the same behavior tests on Python 3.11-3.14.

```sh
python -S -m unittest discover -s tests -p test_scanned_line_storage.py
python -S -m scripts.benchmark_scanned_lines
```

The regression checks fence context, text, opening/closing flags, copy, pickle and
frozen mutation errors. The pinned-baseline benchmark compares all field values on
50000 lines and verifies a table-of-contents output with fenced headings.
CPython 3.12.14/Linux, three traced allocation samples: baseline
5248354/5246018/5246018 bytes versus 3646050 bytes each for slots (~30.5% lower).
Input lines and imports excluded; raw evidence in scanned-line-measurement.json.
This is scanner allocation reduction, not total RSS, faster parsing or build-time
improvement. Full pytest remains in CI.
