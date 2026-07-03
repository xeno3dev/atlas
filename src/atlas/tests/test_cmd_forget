import io
import os
import shutil
import tempfile
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
 
_index_data_dir = Path(tempfile.mkdtemp(prefix="atlas-forget-test-index-"))
os.environ["XDG_DATA_HOME"] = str(_index_data_dir)
 
_fixture_dir = Path(tempfile.mkdtemp(prefix="atlas-forget-test-fixtures-"))
 
from atlas import index
from atlas.cli import cmd_forget
from atlas.errors import ProjectNotFound
 
results = []  # (label, passed, detail)
 
 
def check(label, condition):
    results.append((label, bool(condition), ""))
 
 
def reset_index():
    shutil.rmtree(_index_data_dir, ignore_errors=True)
    _index_data_dir.mkdir(parents=True, exist_ok=True)
 
 
def capture(fn, *args, **kwargs):
    out, err = io.StringIO(), io.StringIO()
    exc = None
    with redirect_stdout(out), redirect_stderr(err):
        try:
            fn(*args, **kwargs)
        except BaseException as e:
            exc = e
    return out.getvalue(), err.getvalue(), exc
 
 
def test_forget_existing_project():
    reset_index()
    idx = index.load()
    index.insert(idx, index.IndexEntry(name="keylo", path="/home/aj/projects/keylo"))
    index.save(idx)
 
    out, err, exc = capture(cmd_forget, "keylo")
 
    check("existing: no exception raised", exc is None)
    check("existing: success message printed", "✓" in out)
    check("existing: message has the real name, not literal braces", "keylo" in out)
 
    idx2 = index.load()
    check("existing: entry actually removed from index", index.find_by_name(idx2, "keylo") is None)
 
 
def test_forget_nonexistent_project():
    reset_index()
    idx = index.load()
    index.insert(idx, index.IndexEntry(name="keylo", path="/x"))
    index.save(idx)
 
    out, err, exc = capture(cmd_forget, "never-registered")
 
    check("nonexistent: raises ProjectNotFound", isinstance(exc, ProjectNotFound))
    check("nonexistent: nothing printed to stdout before the raise", out == "")
 
    idx2 = index.load()
    check("nonexistent: real entry untouched", index.find_by_name(idx2, "keylo") is not None)
 
 
def test_forget_leaves_files_untouched():
    reset_index()
    project_dir = _fixture_dir / "keylo"
    project_dir.mkdir(parents=True, exist_ok=True)
    marker = project_dir / "definitely-still-here.txt"
    marker.write_text("proof this file survives\n")
 
    idx = index.load()
    index.insert(idx, index.IndexEntry(name="keylo", path=str(project_dir)))
    index.save(idx)
 
    _, _, exc = capture(cmd_forget, "keylo")
 
    check("files untouched: no exception raised", exc is None)
    check("files untouched: project directory still exists", project_dir.exists())
    check("files untouched: marker file still exists with original content", marker.read_text() == "proof this file survives\n")
 
 
def test_forget_only_removes_matching_entry():
    reset_index()
    idx = index.load()
    index.insert(idx, index.IndexEntry(name="keylo", path="/x"))
    index.insert(idx, index.IndexEntry(name="zenith", path="/y"))
    index.save(idx)
 
    capture(cmd_forget, "keylo")
 
    idx2 = index.load()
    check("selective: forgotten project is gone", index.find_by_name(idx2, "keylo") is None)
    check("selective: other project untouched", index.find_by_name(idx2, "zenith") is not None)
    check("selective: index has exactly one entry left", len(idx2.projects) == 1)
 
 
def main():
    tests = [
        test_forget_existing_project,
        test_forget_nonexistent_project,
        test_forget_leaves_files_untouched,
        test_forget_only_removes_matching_entry,
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
 
    shutil.rmtree(_index_data_dir, ignore_errors=True)
    shutil.rmtree(_fixture_dir, ignore_errors=True)
 
    if failed:
        raise SystemExit(1)
 
 
if __name__ == "__main__":
    main()