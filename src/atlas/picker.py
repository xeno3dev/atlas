import shutil
import subprocess
import sys
from atlas.index import IndexEntry

def _numbered_fallback(entries: list[IndexEntry]) -> IndexEntry | None:
    print("No fuzzy picker found. Pick a project.")
    for i, entry in enumerate(entries, start=1):
        print(f"    {i}: {entry.name}")
    
    try:
        choice = input("Enter a number: ")
        n = int(choice.strip())
    except (ValueError, EOFError, KeyboardInterrupt):
        print("Invalid choice. Please try again.", file=sys.stderr)
        return None
    
    if not (1 <= n <= len(entries)):
        print("Invalid choice. Please try again.", file=sys.stderr)
        return None
    
    return entries[n - 1]

def fuzzy_pick(entries: list[IndexEntry]) -> IndexEntry | None:
    lines = [f"{entry.name:<20} {entry.path}" for entry in entries]

    picker =  shutil.which("fzf") or shutil.which("sk") or None

    if picker is None:
        return _numbered_fallback(entries)
    
    proc = subprocess.run(
        [picker, "--height", "40%", "--reverse", "--no-sort", "--prompt", "atlas>"],
        input="\n".join(lines),
        capture_output=True,
        text=True
    )

    if proc.returncode != 0:
        return None
    
    selected = proc.stdout.strip()
    if selected == "":
        return None
    
    name = selected.split()[0]
    return next((e for e in entries if e.name == name), None)