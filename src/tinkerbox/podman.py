import logging
import shlex
import subprocess

from tinkerbox import TinkerboxError

logger = logging.getLogger(__name__)


def run_podman(*args: str):
    """
    raises subprocess.CalledProcessError on non-zero exit
    """
    command = ["podman", *args]
    logger.debug("$ %s", shlex.join(command))

    try:
        result = subprocess.run(
            command,
            text=True,
            check=True,
        )
    except FileNotFoundError as exc:
        raise DependencyError("podman executable not found") from exc

    return result.returncode


def run_podman_capture(*args: str) -> str:
    """
    raises subprocess.CalledProcessError on non-zero exit
    """
    command = ["podman", *args]
    logger.debug("$ %s", shlex.join(command))

    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
    except FileNotFoundError as exc:
        raise DependencyError("podman executable not found") from exc

    return result.stdout


class DependencyError(TinkerboxError):
    pass
