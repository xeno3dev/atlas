import io
import os
import shutil
import tempfile
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
 
_index_data_dir = Path(tempfile.mkdtemp(prefix="atlas-open-test-index-"))
os.environ["XDG_DATA_HOME"] = str(_index_data_dir)
 
_fixture_dir = Path(tempfile.mkdtemp(prefix="atlas-open-test-fixtures-"))
 
from atlas import index, config, picker
from atlas.cli import cmd_open
from atlas.errors import ProjectNotFound, NoEditor
 
results = []  # (label, passed, detail)
 
# Env vars this suite touches on the real process — saved once, restored
# at the very end, so a crash mid-run can't leave your real shell env
# looking different after the script exits.
_ENV_KEYS_TOUCHED = ["EDITOR", "VISUAL", "MY_TEST_VAR"]
_original_env = {k: os.environ.get(k) for k in _ENV_KEYS_TOUCHED}
 
 
def check(label, condition):
    results.append((label, bool(condition), ""))
 
 
class patch:
    def __init__(self, obj, attr, replacement):
        self.obj, self.attr, self.replacement = obj, attr, replacement
 
    def __enter__(self):
        self.original = getattr(self.obj, self.attr)
        setattr(self.obj, self.attr, self.replacement)
        return self.replacement
 
    def __exit__(self, *exc_info):
        setattr(self.obj, self.attr, self.original)
 
 
def reset_index():
    shutil.rmtree(_index_data_dir, ignore_errors=True)
    _index_data_dir.mkdir(parents=True, exist_ok=True)
 
 
def clear_env():
    for k in _ENV_KEYS_TOUCHED:
        os.environ.pop(k, None)
 
 
def capture(fn, *args, **kwargs):
    out, err = io.StringIO(), io.StringIO()
    exc = None
    with redirect_stdout(out), redirect_stderr(err):
        try:
            fn(*args, **kwargs)
        except BaseException as e:
            exc = e
    return out.getvalue(), err.getvalue(), exc
 
 
def make_project(name, toml_content=None):
    """Creates a fixture project dir, registers it in the index, and
    optionally writes a .atlas.toml. Returns the project Path."""
    project_dir = _fixture_dir / name
    project_dir.mkdir(parents=True, exist_ok=True)
    if toml_content is not None:
        (project_dir / ".atlas.toml").write_text(toml_content)
 
    idx = index.load()
    index.insert(idx, index.IndexEntry(name=name, path=str(project_dir)))
    index.save(idx)
    return project_dir
 
 
def fake_execvp_recorder():
    """Returns (fake_execvp_fn, captured_dict). The fake just records
    the call instead of replacing the process."""
    captured = {}
 
    def fake_execvp(file, args):
        captured["file"] = file
        captured["args"] = args
 
    return fake_execvp, captured
 
 
def test_named_project_found_launches_correctly():
    reset_index()
    clear_env()
    project_dir = make_project(
        "keylo",
        '''name = "keylo"
editor = "fake-editor"
 
[env]
MY_TEST_VAR = "hello"
 
[hooks]
on_open = ["touch hook-marker.txt"]
on_close = []
''',
    )
 
    fake_execvp, captured = fake_execvp_recorder()
    original_cwd = Path.cwd()
 
    try:
        with patch(os, "execvp", fake_execvp):
            out, err, exc = capture(cmd_open, "keylo")
    finally:
        os.chdir(original_cwd)
 
    check("happy path: no exception raised", exc is None)
    check("happy path: execvp called with the configured editor", captured.get("file") == "fake-editor")
    check(
        "happy path: execvp argv is [editor, project_path]",
        captured.get("args") == ["fake-editor", str(project_dir)],
    )
    check("happy path: env var from config was actually set", os.environ.get("MY_TEST_VAR") == "hello")
    check("happy path: on_open hook actually ran", (project_dir / "hook-marker.txt").exists())
 
    idx = index.load()
    entry = index.find_by_name(idx, "keylo")
    check("happy path: last_opened was saved to disk before the exec call", entry is not None and entry.last_opened is not None)
 
    clear_env()
 
 
def test_named_project_not_found():
    reset_index()
    fake_execvp, captured = fake_execvp_recorder()
 
    with patch(os, "execvp", fake_execvp):
        out, err, exc = capture(cmd_open, "nonexistent")
 
    check("not found: raises ProjectNotFound", isinstance(exc, ProjectNotFound))
    check("not found: execvp was never called", captured == {})
 
 
def test_no_name_no_projects_registered():
    reset_index()
    fake_execvp, captured = fake_execvp_recorder()
 
    with patch(os, "execvp", fake_execvp):
        out, err, exc = capture(cmd_open, None)
 
    check("no projects: raises ProjectNotFound", isinstance(exc, ProjectNotFound))
    check("no projects: execvp was never called", captured == {})
 
 
def test_no_name_picker_selects():
    reset_index()
    clear_env()
    os.environ["EDITOR"] = "fake-editor"
    project_dir = make_project("zenith")
 
    fake_execvp, captured = fake_execvp_recorder()
    original_cwd = Path.cwd()
 
    def fake_pick(entries):
        return next(e for e in entries if e.name == "zenith")
 
    try:
        with patch(os, "execvp", fake_execvp), patch(picker, "fuzzy_pick", fake_pick):
            out, err, exc = capture(cmd_open, None)
    finally:
        os.chdir(original_cwd)
        clear_env()
 
    check("picker selects: no exception raised", exc is None)
    check("picker selects: execvp called for the picked project", captured.get("args") == ["fake-editor", str(project_dir)])
 
 
def test_no_name_picker_cancelled():
    reset_index()
    make_project("keylo")
    fake_execvp, captured = fake_execvp_recorder()
 
    def fake_pick(entries):
        return None  # user hit Esc
 
    with patch(os, "execvp", fake_execvp), patch(picker, "fuzzy_pick", fake_pick):
        out, err, exc = capture(cmd_open, None)
 
    check("picker cancelled: no exception raised (quiet exit)", exc is None)
    check("picker cancelled: execvp was never called", captured == {})
 
 
def test_missing_atlas_toml_falls_back_to_default():
    reset_index()
    clear_env()
    os.environ["EDITOR"] = "fake-editor"
    project_dir = make_project("bare-project")  # no .atlas.toml written
 
    fake_execvp, captured = fake_execvp_recorder()
    original_cwd = Path.cwd()
 
    try:
        with patch(os, "execvp", fake_execvp):
            out, err, exc = capture(cmd_open, "bare-project")
    finally:
        os.chdir(original_cwd)
        clear_env()
 
    check("no config: no exception raised", exc is None)
    check("no config: warns about missing .atlas.toml", "no .atlas.toml" in err.lower())
    check("no config: still launches using $EDITOR", captured.get("file") == "fake-editor")
 
 
def test_editor_priority_config_beats_env():
    reset_index()
    clear_env()
    os.environ["EDITOR"] = "editor-from-env"
    make_project("keylo", 'name = "keylo"\neditor = "editor-from-config"\n')
 
    fake_execvp, captured = fake_execvp_recorder()
    original_cwd = Path.cwd()
    try:
        with patch(os, "execvp", fake_execvp):
            capture(cmd_open, "keylo")
    finally:
        os.chdir(original_cwd)
        clear_env()
 
    check("editor priority: .atlas.toml editor wins over $EDITOR", captured.get("file") == "editor-from-config")
 
 
def test_editor_falls_back_to_env_when_config_unset():
    reset_index()
    clear_env()
    os.environ["EDITOR"] = "editor-from-env"
    make_project("keylo", 'name = "keylo"\n')  # no editor key at all
 
    fake_execvp, captured = fake_execvp_recorder()
    original_cwd = Path.cwd()
    try:
        with patch(os, "execvp", fake_execvp):
            capture(cmd_open, "keylo")
    finally:
        os.chdir(original_cwd)
        clear_env()
 
    check("editor fallback: uses $EDITOR when config doesn't set one", captured.get("file") == "editor-from-env")
 
 
def test_no_editor_anywhere_raises():
    reset_index()
    clear_env()  # no EDITOR, no VISUAL, no config editor
    make_project("keylo", 'name = "keylo"\n')
 
    fake_execvp, captured = fake_execvp_recorder()
    original_cwd = Path.cwd()
    try:
        with patch(os, "execvp", fake_execvp):
            out, err, exc = capture(cmd_open, "keylo")
    finally:
        os.chdir(original_cwd)
 
    check("no editor: raises NoEditor", isinstance(exc, NoEditor))
    check("no editor: execvp was never called", captured == {})
 
 
def test_editor_with_args_split_correctly():
    reset_index()
    clear_env()
    project_dir = make_project("keylo", 'name = "keylo"\neditor = "code --new-window"\n')
 
    fake_execvp, captured = fake_execvp_recorder()
    original_cwd = Path.cwd()
    try:
        with patch(os, "execvp", fake_execvp):
            capture(cmd_open, "keylo")
    finally:
        os.chdir(original_cwd)
 
    check("editor with args: file is just the binary", captured.get("file") == "code")
    check(
        "editor with args: flags are preserved as separate argv entries",
        captured.get("args") == ["code", "--new-window", str(project_dir)],
    )
 
 
def main():
    tests = [
        test_named_project_found_launches_correctly,
        test_named_project_not_found,
        test_no_name_no_projects_registered,
        test_no_name_picker_selects,
        test_no_name_picker_cancelled,
        test_missing_atlas_toml_falls_back_to_default,
        test_editor_priority_config_beats_env,
        test_editor_falls_back_to_env_when_config_unset,
        test_no_editor_anywhere_raises,
        test_editor_with_args_split_correctly,
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
    for k, v in _original_env.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
 
    if failed:
        raise SystemExit(1)
 
 
if __name__ == "__main__":
    main()