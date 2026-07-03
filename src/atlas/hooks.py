import subprocess
import sys
from pathlib import Path

def run_all(hooks, cwd):
    for hook in hooks:
        print("  → " + hook)

        try:
            proc = subprocess.run(hook, cwd=cwd, shell=True)
            if proc.returncode != 0:
                print(f"  ✗ {hook} exited with {proc.returncode}", file=sys.stderr)
        except OSError as e:
            print(f"  ✗ {hook} failed: {e}", file=sys.stderr)

