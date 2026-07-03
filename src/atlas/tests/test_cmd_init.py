import io
import shutil
import tempfile
import os
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
 
_fixture_dir = Path(tempfile.mkdtemp(prefix="atlas-init-test-"))
 
from atlas import config
from atlas.cli import cmd_init, _build_template
from atlas.errors import ConfigExists
 
results = []  # (label, passed, detail)
 
 
def check(label, condition):
    results.append((label, bool(condition), ""))
 
 
def capture(fn, *args, **kwargs):
    """Runs fn, captures stdout/stderr, and captures any exception raised
    (including SystemExit-style BaseExceptions, not just Exception)."""
    out, err = io.StringIO(), io.StringIO()
    exc = None
    with redirect_stdout(out), redirect_stderr(err):
        try:
            fn(*args, **kwargs)
        except BaseException as e:
            exc = e
    return out.getvalue(), err.getvalue(), exc
 
 
def in_fresh_dir(name):
    """Creates a fresh subdir under the fixture dir and returns its Path."""
    d = _fixture_dir / name
    d.mkdir(parents=True, exist_ok=True)
    return d
 
 
def test_build_template_parses_correctly():
    """Tests _build_template() directly — no chdir, no cmd_init() involved.
    Confirms the generated TOML actually round-trips through config.load()
    with the expected defaults, not just that it "looks right"."""
    scratch = _fixture_dir / "template-scratch"
    scratch.mkdir(parents=True, exist_ok=True)
    toml_path = scratch / ".atlas.toml"
    toml_path.write_text(_build_template("keylo"))
 
    cfg = config.load(toml_path)
 
    check("template: name is set correctly", cfg.name == "keylo")
    check("template: editor defaults to None (commented out)", cfg.editor is None)
    check("template: root defaults to '.'", cfg.root == ".")
    check("template: env is empty (commented out)", cfg.env == {})
    check("template: hooks.on_open is empty (commented out)", cfg.hooks.on_open == [])
    check("template: hooks.on_close is empty", cfg.hooks.on_close == [])
 
 
def test_cmd_init_fresh_directory():
    target = in_fresh_dir("fresh-project")
    original_cwd = Path.cwd()
 
    try:
        os.chdir(target)
        out, err, exc = capture(cmd_init)
    finally:
        os.chdir(original_cwd)
 
    check("fresh dir: no exception raised", exc is None)
 
    toml_path = target / ".atlas.toml"
    check("fresh dir: .atlas.toml was created", toml_path.exists())
    check("fresh dir: success message printed", "✓ Created" in out)
    check("fresh dir: success message has the real dir name, not literal braces", "fresh-project" in out)
    check("fresh dir: mentions atlas add as the next step", "atlas add" in out)
 
    if toml_path.exists():
        cfg = config.load(toml_path)
        check("fresh dir: generated config name matches dir name", cfg.name == "fresh-project")
 
 
def test_cmd_init_already_exists():
    target = in_fresh_dir("already-configured")
    toml_path = target / ".atlas.toml"
    original_content = 'name = "do-not-touch-me"\n'
    toml_path.write_text(original_content)
 
    original_cwd = Path.cwd()
    try:
        os.chdir(target)
        out, err, exc = capture(cmd_init)
    finally:
        os.chdir(original_cwd)
 
    check("already exists: raises ConfigExists", isinstance(exc, ConfigExists))
    check("already exists: nothing printed to stdout before the raise", out == "")
    check("already exists: original file content is completely untouched", toml_path.read_text() == original_content)
 
 
def test_root_name_fallback_logic():
    """
    cmd_init() falls back to "project" when cwd.name is empty (the
    filesystem root case). Can't safely chdir into the real root and
    write a file there in a test, so this checks the exact fallback
    expression cmd_init() uses instead of exercising the full function
    against a real root directory.
    """
    check("root fallback: Path('/').name is genuinely empty", Path("/").name == "")
    check(
        "root fallback: 'cwd.name or project' produces 'project' for that case",
        (Path("/").name or "project") == "project",
    )
 
 
def main():
    tests = [
        test_build_template_parses_correctly,
        test_cmd_init_fresh_directory,
        test_cmd_init_already_exists,
        test_root_name_fallback_logic,
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