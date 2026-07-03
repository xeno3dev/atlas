class AtlasError(Exception):
    """Base class for all atlas errors"""

class IndexCorrupt(AtlasError):
    def __init__(self, reason: str):
        super().__init__(
            f"Your index file has corrupted: {reason}"
            "Delete ~/.local/share/atlas/index.json and re-add your projects."
        )

class ConfigInvalid(AtlasError):
    def __init__(self, reason: str):
        super().__init__(
            f"Your config file is invalid: {reason}"
        )

class ConfigExists(AtlasError):
    def __init__(self, reason: str):
        super().__init__(
            f"A config file already exists here! {reason}"
        )

class ProjectNotFound(AtlasError):
    def __init__(self, name: str):
        super().__init__(f"Your project named {name} was not found. Please run `atlas list` to see all projects.")

class ProjectAlreadyExists(AtlasError):
    def __init__(self, name: str):
        super().__init__(f"A project named {name} already exists. Please run `atlas forget` first if you would like to overwrite it's entry.")

class NoEditor(AtlasError):
    def __init__(self):
        super().__init__('No editor has been configured for this project. Add `editor` to your .atlas.toml or set $EDITOR.')