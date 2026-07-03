import io
import os
import shutil
import tempfile
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
 
_fixture_dir = Path(tempfile.mkdtemp(prefix="atlas-which-test-"))
 
from atlas.cli import cmd_which
 
results = []  # (label, passed, detail)
 
 
def check(label, condition):
    results.append((label, bool(condition), ""))
 
 
def capture(fn, *args, **kwargs):
    out, err = io.StringIO(), io.StringIO()
    exc = None
    with redirect_stdout(out), redirect_stderr(err):
        try:
            fn(*args, **kwargs)
        except BaseException as e:
            exc = e
    return out.getvalue(), err.getvalue(), exc
 
 
def run_which_in(directory):
    """chdir into `directory`, run cmd_which(), always restore cwd after."""
    original_cwd = Path.cwd()
    try:
        os.chdir(directory)
        return capture(cmd_which)
    finally:
        os.chdir(original_cwd)
 
 
def test_found_immediately():
    project_dir = _fixture_dir / "immediate-project"
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / ".atlas.toml").write_text('name = "immediate-project"\n')
 
    out, err, exc = run_which_in(project_dir)
 
    check("found immediately: no exception raised", exc is None)
    check("found immediately: prints exactly the project name, nothing else", out.strip() == "immediate-project")
    check("found immediately: no stderr output on the success path", err == "")
 
 
def test_found_by_walking_up():
    top = _fixture_dir / "nested-project"
    deep = top / "src" / "components" / "deeply" / "nested"
    deep.mkdir(parents=True, exist_ok=True)
    (top / ".atlas.toml").write_text('name = "nested-project"\n')
 
    out, err, exc = run_which_in(deep)
 
    check("walk up: no exception raised", exc is None)
    check("walk up: finds the config several directories above and prints its name", out.strip() == "nested-project")
 
 
def test_not_found():
    target = _fixture_dir / "isolated-not-found"
    target.mkdir(parents=True, exist_ok=True)
 
    original_exists = Path.exists
 
    def always_false(self):
        return False
 
    Path.exists = always_false
    try:
        out, err, exc = run_which_in(target)
    finally:
        Path.exists = original_exists
 
    check("not found: raises SystemExit", isinstance(exc, SystemExit))
    if isinstance(exc, SystemExit):
        check("not found: exit code is 1", exc.code == 1)
    check("not found: message goes to stderr, not stdout", err.strip() != "" and out == "")
 
 
def main():
    tests = [
        test_found_immediately,
        test_found_by_walking_up,
        test_not_found,
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
 
    shutil.rmtree(_fixture_dir, ignore_errors=True)
 
    if failed:
        raise SystemExit(1)
 
 
if __name__ == "__main__":
    main()
