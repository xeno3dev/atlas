import io
import os
import shutil
import tempfile
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
 
_index_data_dir = Path(tempfile.mkdtemp(prefix="atlas-add-test-index-"))
os.environ["XDG_DATA_HOME"] = str(_index_data_dir)
 
_fixture_dir = Path(tempfile.mkdtemp(prefix="atlas-add-test-fixtures-"))
 
from atlas import index
from atlas.cli import cmd_add
from atlas.errors import ProjectAlreadyExists
 
results = []  # (label, passed, detail)
 
 
def check(label, condition):
    results.append((label, bool(condition), ""))
 
 
def reset_index():
    shutil.rmtree(_index_data_dir, ignore_errors=True)
    _index_data_dir.mkdir(parents=True, exist_ok=True)
 
 
def capture(fn, *args, **kwargs):
    """Runs fn, captures stdout/stderr, and captures any exception raised
    (including SystemExit, which is a BaseException, not an Exception —
    a plain `except Exception` would let it slip through uncaught)."""
    out, err = io.StringIO(), io.StringIO()
    exc = None
    with redirect_stdout(out), redirect_stderr(err):
        try:
            fn(*args, **kwargs)
        except BaseException as e:
            exc = e
    return out.getvalue(), err.getvalue(), exc
 
 
def test_missing_path():
    reset_index()
    missing = str(_fixture_dir / "definitely-does-not-exist")
 
    out, err, exc = capture(cmd_add, missing)
 
    check("missing path: raises SystemExit", isinstance(exc, SystemExit))
    if isinstance(exc, SystemExit):
        check("missing path: exit code is 1", exc.code == 1)
    check("missing path: something printed to stderr", err.strip() != "")
    check("missing path: error message mentions the actual path", missing in err)
    check("missing path: nothing printed to stdout", out == "")
 
    idx = index.load()
    check("missing path: nothing got registered", len(idx.projects) == 0)
 
 
def test_no_atlas_toml():
    reset_index()
    proj_dir = _fixture_dir / "no-config-project"
    proj_dir.mkdir(parents=True, exist_ok=True)
 
    out, err, exc = capture(cmd_add, str(proj_dir))
 
    check("no config: no exception raised", exc is None)
    check("no config: warns about missing .atlas.toml", "No .atlas.toml found" in err)
    check("no config: success message printed to stdout", "✓ Registered" in out)
    check("no config: success message has the real name, not literal braces", "no-config-project" in out)
 
    idx = index.load()
    entry = index.find_by_name(idx, "no-config-project")
    check("no config: registered in index", entry is not None)
    if entry:
        check("no config: path matches resolved dir", Path(entry.path) == proj_dir.resolve())
 
 
def test_with_atlas_toml():
    reset_index()
    proj_dir = _fixture_dir / "configured-project"
    proj_dir.mkdir(parents=True, exist_ok=True)
    (proj_dir / ".atlas.toml").write_text('name = "custom-name"\n')
 
    out, err, exc = capture(cmd_add, str(proj_dir))
 
    check("with config: no exception raised", exc is None)
    check("with config: no missing-config warning printed", "No .atlas.toml found" not in err)
    check("with config: uses name from .atlas.toml, not dir basename", "custom-name" in out)
 
    idx = index.load()
    check("with config: registered under config's name", index.find_by_name(idx, "custom-name") is not None)
    check("with config: NOT registered under the dir basename", index.find_by_name(idx, "configured-project") is None)
 
 
def test_duplicate_name():
    reset_index()
    proj_dir = _fixture_dir / "dup-project"
    proj_dir.mkdir(parents=True, exist_ok=True)
 
    _, _, exc1 = capture(cmd_add, str(proj_dir))
    check("duplicate: first add succeeds", exc1 is None)
 
    _, _, exc2 = capture(cmd_add, str(proj_dir))
    check("duplicate: second add raises ProjectAlreadyExists", isinstance(exc2, ProjectAlreadyExists))
 
    idx = index.load()
    matches = [e for e in idx.projects if e.name == "dup-project"]
    check("duplicate: index has exactly one entry, not two", len(matches) == 1)
 
 
def test_default_to_cwd():
    reset_index()
    original_cwd = Path.cwd()
    target_dir = _fixture_dir / "cwd-target"
    target_dir.mkdir(parents=True, exist_ok=True)
 
    try:
        os.chdir(target_dir)
        _, _, exc = capture(cmd_add, None)
    finally:
        os.chdir(original_cwd)
 
    check("default to cwd: no exception raised", exc is None)
 
    idx = index.load()
    entry = index.find_by_name(idx, "cwd-target")
    check("default to cwd: registered under cwd's name", entry is not None)
    if entry:
        check("default to cwd: path matches resolved cwd", Path(entry.path) == target_dir.resolve())
 
 
def main():
    tests = [
        test_missing_path,
        test_no_atlas_toml,
        test_with_atlas_toml,
        test_duplicate_name,
        test_default_to_cwd,
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