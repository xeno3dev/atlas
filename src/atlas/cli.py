import typer
from typing import Optional

app = typer.Typer(help="a tmux-free project switcher/launcher for developers")

@app.command()
def open(name: Optional[str] = typer.Argument(None, help="project name (fuzzy pick if omitted)")):
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