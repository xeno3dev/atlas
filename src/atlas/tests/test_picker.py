import builtins
import subprocess
from atlas.index import IndexEntry
from atlas.picker import fuzzy_pick, _numbered_fallback
 
results = []  # (label, passed, detail)
 
 
def check(label, condition):
    results.append((label, bool(condition), ""))
 
 
def sample_entries():
    return [
        IndexEntry(name="keylo", path="/home/aj/projects/keylo"),
        IndexEntry(name="zenith", path="/home/aj/projects/zenith"),
        IndexEntry(name="xenodeal", path="/home/aj/projects/xenodeal"),
    ]
 
 
class patch:
    """Small context manager for swapping a module/class attribute out
    and guaranteeing it's restored, even if the test body raises."""
 
    def __init__(self, obj, attr, replacement):
        self.obj = obj
        self.attr = attr
        self.replacement = replacement
 
    def __enter__(self):
        self.original = getattr(self.obj, self.attr)
        setattr(self.obj, self.attr, self.replacement)
        return self.replacement
 
    def __exit__(self, *exc_info):
        setattr(self.obj, self.attr, self.original)
 
 
# ── fuzzy_pick() with a picker "available" ──────────────────────────
 
def test_successful_selection():
    entries = sample_entries()
    fake_stdout = f"{'zenith':<20} /home/aj/projects/zenith\n"
 
    def fake_which(name):
        return "/usr/bin/fzf" if name == "fzf" else None
 
    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(args=args, returncode=0, stdout=fake_stdout)
 
    with patch(__import__("shutil"), "which", fake_which), patch(subprocess, "run", fake_run):
        result = fuzzy_pick(entries)
 
    check("successful selection: returns the right entry", result is not None and result.name == "zenith")
 
 
def test_cancelled_nonzero_returncode():
    entries = sample_entries()
 
    def fake_which(name):
        return "/usr/bin/fzf" if name == "fzf" else None
 
    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(args=args, returncode=130, stdout="")
 
    with patch(__import__("shutil"), "which", fake_which), patch(subprocess, "run", fake_run):
        result = fuzzy_pick(entries)
 
    check("cancelled (nonzero exit): returns None", result is None)
 
 
def test_empty_stdout():
    entries = sample_entries()
 
    def fake_which(name):
        return "/usr/bin/fzf" if name == "fzf" else None
 
    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="")
 
    with patch(__import__("shutil"), "which", fake_which), patch(subprocess, "run", fake_run):
        result = fuzzy_pick(entries)
 
    check("empty stdout (exit 0, nothing selected): returns None", result is None)
 
 
def test_name_parsing_extracts_just_the_token():
    """Regression test for the .split('\\n')[0] bug — fzf's actual
    output is the padded display line, not something containing a
    real newline. Only .split() (whitespace) correctly isolates the
    name from the trailing path."""
    entries = sample_entries()
    fake_stdout = f"{'keylo':<20} /home/aj/projects/keylo\n"
 
    def fake_which(name):
        return "/usr/bin/fzf" if name == "fzf" else None
 
    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(args=args, returncode=0, stdout=fake_stdout)
 
    with patch(__import__("shutil"), "which", fake_which), patch(subprocess, "run", fake_run):
        result = fuzzy_pick(entries)
 
    check("name parsing: matches the correct entry, not None or the wrong one", result is not None and result.name == "keylo")
 
 
def test_subprocess_called_with_text_mode():
    """Regression test for the missing text=True bug — without it,
    a str input= raises TypeError before this even gets to run for real."""
    entries = sample_entries()
    captured = {}
 
    def fake_which(name):
        return "/usr/bin/fzf" if name == "fzf" else None
 
    def fake_run(*args, **kwargs):
        captured["kwargs"] = kwargs
        return subprocess.CompletedProcess(args=args, returncode=0, stdout=f"{'keylo':<20} /x\n")
 
    with patch(__import__("shutil"), "which", fake_which), patch(subprocess, "run", fake_run):
        fuzzy_pick(entries)
 
    check("subprocess call: text=True was passed", captured.get("kwargs", {}).get("text") is True)
 
 
def test_no_matching_entry_returns_none_not_crash():
    entries = sample_entries()
    fake_stdout = "some-unknown-project      /nowhere\n"
 
    def fake_which(name):
        return "/usr/bin/fzf" if name == "fzf" else None
 
    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(args=args, returncode=0, stdout=fake_stdout)
 
    with patch(__import__("shutil"), "which", fake_which), patch(subprocess, "run", fake_run):
        result = fuzzy_pick(entries)
 
    check("no matching entry: returns None instead of raising StopIteration", result is None)
 
 
# ── fuzzy_pick() dispatching to the fallback ─────────────────────────
 
def test_falls_back_to_numbered_when_no_picker():
    """Regression test for the _numbered_fallback(lines) vs (entries)
    bug — passing the wrong type crashes with AttributeError on the
    first loop iteration."""
    entries = sample_entries()
 
    def fake_which(name):
        return None  # neither fzf nor sk found
 
    def fake_input(prompt=""):
        return "2"
 
    with patch(__import__("shutil"), "which", fake_which), patch(builtins, "input", fake_input):
        result = fuzzy_pick(entries)
 
    check("no picker installed: falls back and returns a real entry", result is not None and result.name == "zenith")
 
 
# ── _numbered_fallback() in isolation ────────────────────────────────
 
def test_fallback_valid_choice():
    entries = sample_entries()
 
    def fake_input(prompt=""):
        return "1"
 
    with patch(builtins, "input", fake_input):
        result = _numbered_fallback(entries)
 
    check("fallback valid choice: returns the right entry", result is not None and result.name == "keylo")
 
 
def test_fallback_out_of_range():
    entries = sample_entries()
 
    def fake_input(prompt=""):
        return "99"
 
    with patch(builtins, "input", fake_input):
        result = _numbered_fallback(entries)
 
    check("fallback out of range: returns None", result is None)
 
 
def test_fallback_non_numeric():
    entries = sample_entries()
 
    def fake_input(prompt=""):
        return "banana"
 
    with patch(builtins, "input", fake_input):
        result = _numbered_fallback(entries)
 
    check("fallback non-numeric input: returns None", result is None)
 
 
def test_fallback_eof_error():
    """Regression test for input() being outside the try block —
    if that's not fixed, this EOFError propagates uncaught instead
    of being handled."""
    entries = sample_entries()
 
    def raising_input(prompt=""):
        raise EOFError()
 
    with patch(builtins, "input", raising_input):
        result = _numbered_fallback(entries)
 
    check("fallback EOFError from input(): returns None, doesn't propagate", result is None)
 
 
def test_fallback_keyboard_interrupt():
    entries = sample_entries()
 
    def raising_input(prompt=""):
        raise KeyboardInterrupt()
 
    with patch(builtins, "input", raising_input):
        result = _numbered_fallback(entries)
 
    check("fallback KeyboardInterrupt from input(): returns None, doesn't propagate", result is None)
 
 
def main():
    tests = [
        test_successful_selection,
        test_cancelled_nonzero_returncode,
        test_empty_stdout,
        test_name_parsing_extracts_just_the_token,
        test_subprocess_called_with_text_mode,
        test_no_matching_entry_returns_none_not_crash,
        test_falls_back_to_numbered_when_no_picker,
        test_fallback_valid_choice,
        test_fallback_out_of_range,
        test_fallback_non_numeric,
        test_fallback_eof_error,
        test_fallback_keyboard_interrupt,
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
 
    if failed:
        raise SystemExit(1)
 
 
if __name__ == "__main__":
    main()