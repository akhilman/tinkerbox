import os
from collections.abc import Iterator
from pathlib import Path

APP_ID = "io.github.akhilman.tinkerbox"
APP_NAME = "tinkerbox"


def config_paths() -> Iterator[Path]:
    """Return the conventional system and XDG user config paths.

    Paths are returned without checking whether they currently exist.
    """
    # XDG_CONFIG_HOME defaults to ~/.config.
    xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config_home:
        config_home = Path(xdg_config_home).expanduser()
        if not config_home.is_absolute():
            raise ValueError("XDG_CONFIG_HOME must be an absolute path")
    else:
        config_home = Path.home() / ".config"

    for dir in (config_home, Path("/etc")):
        dir = dir / APP_NAME
        if dir.is_dir():
            yield dir


class TinkerboxError(Exception):
    pass
