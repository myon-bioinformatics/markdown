"""Run from repo root: python -S -m scripts.benchmark_scanned_lines."""
import json, subprocess, sys, tracemalloc, types
import markdown


def main():
    sha='cac8b72597e6b75d67653ee86a684707812406ca'
    old=types.ModuleType('baseline_markdown')
    sys.modules[old.__name__]=old
    exec(subprocess.check_output(['git','show',sha+':markdown.py']),old.__dict__)
    lines=['ordinary','```py','print(1)','```']*12500
    results={}
    expected=None
    for name,module in [('baseline',old),('slotted',markdown)]:
        samples=[]
        for _ in range(3):
            tracemalloc.start()
            scanned=module._scan_lines(lines)
            samples.append(tracemalloc.get_traced_memory()[1])
            tracemalloc.stop()
            fields=[(r.text,r.in_fenced_code,r.is_fence_open,r.is_fence_close) for r in scanned]
            if expected is None:expected=fields
            if fields != expected:
                raise SystemExit("scanner field mismatch")
            del scanned
        results[name]=samples
    content='# Hello\n\n```py\n# hidden\n```\n## World\n'
    if old.table_of_contents(content) != markdown.table_of_contents(content):
        raise SystemExit("table of contents mismatch")
    print(json.dumps({'python':sys.version,'baseline_sha':sha,'lines':len(lines),'peak_bytes':results,
                      'scope':'scanner allocations only; source lines/import excluded'},indent=2))


if __name__=='__main__':main()
