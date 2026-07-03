import io
import os
import shutil
import tempfile
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
 
_test_data_dir = Path(tempfile.mkdtemp(prefix="atlas-list-test-"))
os.environ["XDG_DATA_HOME"] = str(_test_data_dir)
 
from atlas import index
from atlas.cli import cmd_list
 
results = []  # (label, passed, detail)
 
 
def check(label, condition):
    results.append((label, bool(condition), ""))
 
 
def reset():
    shutil.rmtree(_test_data_dir, ignore_errors=True)
    _test_data_dir.mkdir(parents=True, exist_ok=True)
 
 
def capture(fn, *args, **kwargs):
    buf = io.StringIO()
    with redirect_stdout(buf):
        fn(*args, **kwargs)
    return buf.getvalue()
 
 
def test_empty_index():
    reset()
    output = capture(cmd_list)
    lines = output.strip("\n").split("\n")
 
    check(
        "empty index: prints the no-projects message",
        "No projects have been registered yet. Run `atlas add [path]` to add one." in output,
    )
    check("empty index: prints exactly one line, nothing else", len(lines) == 1)
 
 
def test_single_never_opened():
    reset()
    idx = index.load()
    index.insert(idx, index.IndexEntry(name="keylo", path="/home/aj/projects/keylo"))
    index.save(idx)
 
    output = capture(cmd_list)
 
    check("single entry: name appears", "keylo" in output)
    check("single entry: path appears", "/home/aj/projects/keylo" in output)
    check("single entry: shows 'never' for unset last_opened", "never" in output)
 
 
def test_sorting_and_formatting():
    reset()
    idx = index.load()
 
    # Deliberately inserted out of order — proves cmd_list() actually
    # sorts rather than just preserving insertion order.
    never_opened = index.IndexEntry(name="xenodeal", path="/home/aj/projects/xenodeal")
    older = index.IndexEntry(
        name="zenith",
        path="/home/aj/projects/zenith",
        last_opened=datetime(2026, 6, 20, 10, 0, tzinfo=timezone.utc).isoformat(),
    )
    newer = index.IndexEntry(
        name="keylo",
        path="/home/aj/projects/keylo",
        last_opened=datetime(2026, 6, 29, 14, 23, tzinfo=timezone.utc).isoformat(),
    )
 
    for entry in (never_opened, older, newer):
        index.insert(idx, entry)
    index.save(idx)
 
    output = capture(cmd_list)
    lines = output.strip("\n").split("\n")
 
    check("sorting: exactly 3 lines printed", len(lines) == 3)
 
    if len(lines) == 3:
        check("sorting: newest-opened project first", lines[0].startswith("keylo"))
        check("sorting: older-opened project second", lines[1].startswith("zenith"))
        check("sorting: never-opened project last", lines[2].startswith("xenodeal"))
 
        expected_keylo_line = f"{'keylo':<20} {'/home/aj/projects/keylo':<50} 2026-06-29 14:23"
        expected_zenith_line = f"{'zenith':<20} {'/home/aj/projects/zenith':<50} 2026-06-20 10:00"
 
        check("formatting: keylo line matches exact column spec", lines[0] == expected_keylo_line)
        check("formatting: zenith line matches exact column spec", lines[1] == expected_zenith_line)
        check("formatting: xenodeal line shows 'never'", "never" in lines[2])
 
 
def main():
    tests = [
        test_empty_index,
        test_single_never_opened,
        test_sorting_and_formatting,
    ]
 
    for t in tests:
        print(f"\n── {t.__name__} " + "─" * max(0, 50 - len(t.__name__)))
        start = len(results)
        try:
            t()
        except Exception as e:
            results.append((f"{t.__name__} crashed", False, f"{type(e).__name__}: {e}"))
        for label, ok, detail in results[start:]:
            mark = "✓" if ok else "✗"
            extra = f" — {detail}" if detail else ""
            print(f"  {mark} {label}{extra}")
 
    passed = sum(1 for _, ok, _ in results if ok)
    failed = sum(1 for _, ok, _ in results if not ok)
    print(f"\n{passed} passed, {failed} failed")
 
    shutil.rmtree(_test_data_dir, ignore_errors=True)
 
    if failed:
        raise SystemExit(1)
 
 
if __name__ == "__main__":
    main()