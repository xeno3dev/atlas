import shutil
import tempfile
from pathlib import Path
 
from atlas import config
from atlas.errors import ConfigInvalid
 
_test_dir = Path(tempfile.mkdtemp(prefix="atlas-config-test-"))
 
results = []  # (label, passed, detail)
 
 
def check(label, condition):
    results.append((label, bool(condition), ""))
 
 
def write_toml(text: str) -> Path:
    """Write text to a fresh .atlas.toml in the scratch dir, return its path."""
    path = _test_dir / ".atlas.toml"
    path.write_text(text)
    return path
 
 
def test_load_full_config():
    path = write_toml('''
name = "keylo"
editor = "hx"
root = "."
 
[env]
FLASK_ENV = "development"
DATABASE_URL = "postgresql://localhost/keylo_dev"
 
[hooks]
on_open = ["source .venv/bin/activate", "echo ready"]
on_close = ["echo bye"]
''')
    cfg = config.load(path)
 
    check("full config: name", cfg.name == "keylo")
    check("full config: editor", cfg.editor == "hx")
    check("full config: root", cfg.root == ".")
    check("full config: env", cfg.env == {
        "FLASK_ENV": "development",
        "DATABASE_URL": "postgresql://localhost/keylo_dev",
    })
    check("full config: hooks.on_open", cfg.hooks.on_open == ["source .venv/bin/activate", "echo ready"])
    check("full config: hooks.on_close", cfg.hooks.on_close == ["echo bye"])
 
 
def test_load_minimal_config():
    path = write_toml('name = "zenith"\n')
    cfg = config.load(path)
 
    check("minimal config: name", cfg.name == "zenith")
    check("minimal config: editor defaults to None", cfg.editor is None)
    check("minimal config: root defaults to '.'", cfg.root == ".")
    check("minimal config: env defaults to {}", cfg.env == {})
    check("minimal config: on_open defaults to []", cfg.hooks.on_open == [])
    check("minimal config: on_close defaults to []", cfg.hooks.on_close == [])
 
 
def test_load_missing_name():
    path = write_toml('editor = "hx"\n')
 
    raised = False
    try:
        config.load(path)
    except ConfigInvalid:
        raised = True
    check("missing name field: raises ConfigInvalid", raised)
 
 
def test_load_malformed_toml():
    path = write_toml('name = "unterminated string\n')
 
    raised = False
    try:
        config.load(path)
    except ConfigInvalid:
        raised = True
    check("malformed TOML: raises ConfigInvalid", raised)
 
 
def test_load_missing_file():
    missing_path = _test_dir / "does-not-exist.atlas.toml"
 
    raised_correctly = False
    try:
        config.load(missing_path)
    except FileNotFoundError:
        raised_correctly = True
    check(
        "missing file: raises FileNotFoundError, not ConfigInvalid "
        "(load() doesn't check existence — that's the caller's job)",
        raised_correctly,
    )
 
 
def test_default():
    cfg = config.default(Path("/home/aj/projects/keylo"))
 
    check("default: name comes from dir basename", cfg.name == "keylo")
    check("default: editor is None", cfg.editor is None)
    check("default: root is '.'", cfg.root == ".")
    check("default: env is {}", cfg.env == {})
    check("default: on_open is []", cfg.hooks.on_open == [])
    check("default: on_close is []", cfg.hooks.on_close == [])
 
 
def main():
    tests = [
        test_load_full_config,
        test_load_minimal_config,
        test_load_missing_name,
        test_load_malformed_toml,
        test_load_missing_file,
        test_default,
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
 
    shutil.rmtree(_test_dir, ignore_errors=True)
 
    if failed:
        raise SystemExit(1)
 
 
if __name__ == "__main__":
    main()
