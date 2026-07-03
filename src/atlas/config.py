from dataclasses import dataclass, field
from pathlib import Path

import tomllib
from atlas.errors import ConfigInvalid

@dataclass
class HookConfig:
    on_open: list[str] = field(default_factory=list)
    on_close: list[str] = field(default_factory=list)

@dataclass
class ProjectConfig:
    name: str
    editor: str | None = None
    root: str = "."
    env: dict[str, str] = field(default_factory=dict)
    hooks: HookConfig = field(default_factory=HookConfig)

def load(path: Path) -> ProjectConfig:
    try:
        data = tomllib.loads(path.read_text())
    except tomllib.TOMLDecodeError as e:
        raise ConfigInvalid(f"Failed to load config: {e}")
    
    if "name" not in data:
        raise ConfigInvalid("Config must have a name")

    hooks_data = data.get("hooks", {})

    project = ProjectConfig(
        name=data["name"],
        editor=data.get("editor"),
        root=data.get("root", "."),
        env=data.get("env", {}),
        hooks=HookConfig(
            on_open=hooks_data.get("on_open", []),
            on_close=hooks_data.get("on_close", [])
        )
    )
    return project

def default(dir_path: Path) -> ProjectConfig:
    return ProjectConfig(
        name=dir_path.name,
        editor=None,
        root=".",
        env={},
        hooks=HookConfig(
            on_open=[],
            on_close=[]
        )
    )

