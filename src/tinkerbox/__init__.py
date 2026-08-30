import os
from collections.abc import Iterator
from importlib.metadata import packages_distributions
from pathlib import Path


def package_name() -> str:

    package = __package__
    assert package
    module_name = package.split(".")[0]
    distributions = packages_distributions().get(module_name, [])

    if not distributions:
        raise RuntimeError(f"Could not determine distribution for {module_name!r}")

    return distributions[0]


def config_paths() -> Iterator[Path]:
    """Return the conventional system and XDG user config paths.

    Paths are returned without checking whether they currently exist.
    """
    pkg_name = package_name()

    # XDG_CONFIG_HOME defaults to ~/.config.
    xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config_home:
        config_home = Path(xdg_config_home).expanduser()
        if not config_home.is_absolute():
            raise ValueError("XDG_CONFIG_HOME must be an absolute path")
    else:
        config_home = Path.home() / ".config"

    for dir in (config_home, Path("/etc")):
        dir = dir / pkg_name
        if dir.is_dir():
            yield dir
