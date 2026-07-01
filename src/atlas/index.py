from dataclasses import dataclass, field

import json
from pathlib import Path
from datetime import datetime, timezone
from platformdirs import user_data_path
from atlas.errors import IndexCorrupt

@dataclass
class IndexEntry:
    name: str
    path: str
    last_opened: str | None = None

@dataclass
class AtlasIndex:
    version: int
    projects: list[IndexEntry] = field(default_factory=list)

def _index_path() -> Path:
    return user_data_path("atlas") / "index.json"

def load() -> AtlasIndex:
    path = _index_path()

    if not path.exists():
        return AtlasIndex(version=1, projects=[])
    
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        raise IndexCorrupt(f"Failed to load index: {e}")
    
    projects = [IndexEntry(**p) for p in data["projects"]]
    return AtlasIndex(version=data["version"], projects=projects)

def save(index: AtlasIndex):
    path = _index_path()
    tmp = path.with_suffix(".tmp")

    path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "version": index.version,
        "projects": [vars(p) for p in index.projects]
    }

    
    tmp.write_text(json.dumps(data, indent=2))
    tmp.replace(path)

def find_by_name(index: AtlasIndex, name: str) -> IndexEntry | None:
    return next((x for x in index.projects if x.name == name), None)

def insert(index: AtlasIndex, entry: IndexEntry):
    index.projects.append(entry)

def remove(index: AtlasIndex, name: str):
    index.projects = [x for x in index.projects if x.name != name]

def update_last_opened(index: AtlasIndex, name: str):
    entry = find_by_name(index, name)
    if entry:
        entry.last_opened = datetime.now(timezone.utc).isoformat()