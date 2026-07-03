import typer
from typing import Optional

from datetime import datetime
from atlas import index

from pathlib import Path
from atlas.errors import ProjectNotFound, ProjectAlreadyExists, ConfigExists, NoEditor
from atlas import config
from atlas.index import IndexEntry
import sys

from atlas import picker
import os
from atlas import hooks
import shlex

app = typer.Typer(help="a tmux-free project switcher/launcher for developers")

@app.command(name="open")
def open_cmd(name: Optional[str] = typer.Argument(None, help="project name (fuzzy pick if omitted)")):
    cmd_open(name)

@app.command()
def add(path: Optional[str] = typer.Argument(None, help="project path to register (defaults to cwd)")):
    cmd_add(path)

@app.command(name="list")
def list_cmd():
    cmd_list()

@app.command()
def init():
    cmd_init()

@app.command()
def forget(name: str = typer.Argument(..., help="project name to remove from registry")):
    cmd_forget(name)

@app.command()
def which():
    cmd_which()

def cmd_add(path_arg):
    path = Path(path_arg) if path_arg else Path.cwd()

    if not path.exists():
        print(f"No such directory: {path}", file=sys.stderr)
        sys.exit(1)
    
    path = path.resolve()

    toml_path = path / ".atlas.toml"

    if toml_path.exists():
        cfg = config.load(toml_path)
        name = cfg.name
    else:
        name = path.name
        print(f"No .atlas.toml found for {path}. Using {name} as project name. Run atlas init to create one.", file=sys.stderr)
    idx = index.load()

    if index.find_by_name(idx, name) is not None:
        raise ProjectAlreadyExists(name)
    
    entry = IndexEntry(name, str(path), last_opened=None)
    index.insert(idx, entry)
    index.save(idx)

    print(f"✓ Registered '{name}' → {path}")

def cmd_list():
    idx = index.load()

    if not idx.projects:
        print("No projects have been registered yet. Run `atlas add [path]` to add one.")
        return
    
    opened = sorted(
        [e for e in idx.projects if e.last_opened is not None],
        key=lambda e: e.last_opened,
        reverse=True
    )
    never = [e for e in idx.projects if e.last_opened is None]
    entries = opened + never

    for entry in entries:
        last = entry.last_opened
        last = datetime.fromisoformat(last).strftime("%Y-%m-%d %H:%M") if last else "never"
        print(f"{entry.name:<20} {entry.path:<50} {last}")

def _build_template(name: str) -> str:
    return f'''name = "{name}"
# editor = "nvim"   # override $EDITOR env for this project

[env]
# DATABASE_URL = "postgres://localhost/{name}_dev"
# FLASK_ENV = "development"

[hooks]
on_open = [
    # "source .venv/bin/activate",
    # "echo '{name} is ready to go!'",
]
on_close = []   # run after exiting the project
                # will be apart of atlas v2; wip
'''

def cmd_init():
    cwd = Path.cwd()
    toml_path = cwd / ".atlas.toml"

    if toml_path.exists():
        raise ConfigExists("If you would like to override the current config, please delete it first.")
    
    name = cwd.name or "project"

    toml_path.write_text(_build_template(name))

    print(f"✓ Created .atlas.toml for '{name}'!")
    print("  Edit it to match your project's needs and run `atlas add` to register it.")

def cmd_forget(name: str):
    idx = index.load()

    if index.find_by_name(idx, name) is None:
        raise ProjectNotFound(name)

    index.remove(idx, name)
    index.save(idx)

    print(f"✓ Removed '{name}' from registry. Project files have not been deleted.")

def cmd_which():
    current = Path.cwd()

    while True:
        toml_path = current / ".atlas.toml"

        if toml_path.exists():
            cfg = config.load(toml_path)
            print(cfg.name)
            return

        if current.parent == current:
            break

        current = current.parent

    print("Not inside an atlas project.", file=sys.stderr)
    raise SystemExit(1)

def cmd_open(name_arg: str | None):
    idx = index.load()

    if name_arg:
        entry = index.find_by_name(idx, name_arg)
        if entry is None:
            raise ProjectNotFound(name_arg)
    else:
        if not idx.projects:
            raise ProjectNotFound("(no projects registered)")
        entry = picker.fuzzy_pick(idx.projects)
        if entry is None:
            return
    
    project_path = Path(entry.path)
    toml_path = project_path / ".atlas.toml"

    if toml_path.exists(): cfg = config.load(toml_path)
    else: print("no .atlas.toml was found, opening bare directory", file=sys.stderr); cfg = config.default(project_path)

    for key, value in cfg.env.items():
        os.environ[key] = str(value)

    hooks.run_all(cfg.hooks.on_open, project_path)

    index.update_last_opened(idx, entry.name)
    index.save(idx)

    editor = cfg.editor or os.environ.get("EDITOR") or os.environ.get("VISUAL")

    if not editor:
        raise NoEditor()
    
    editor_cmd = shlex.split(editor)
    
    os.chdir(project_path)
    os.execvp(editor_cmd[0], editor_cmd + [str(project_path)])