import logging
import shlex
import subprocess

from tinkerbox import TinkerboxError

logger = logging.getLogger(__name__)


def run_podman(*args: str):
    run("podman", *args)


def run_podman_capture(*args: str) -> str:
    return run_capture("podman", *args)


def run(cmd: str, *args: str):
    """
    raises subprocess.CalledProcessError on non-zero exit
    """
    command = [cmd, *args]
    logger.debug("$ %s", shlex.join(command))

    try:
        result = subprocess.run(
            command,
            text=True,
            check=True,
        )
    except FileNotFoundError as exc:
        raise DependencyError(f"{cmd} executable not found") from exc

    return result.returncode


def run_capture(cmd: str, *args: str) -> str:
    """
    raises subprocess.CalledProcessError on non-zero exit
    """
    command = [cmd, *args]
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
        raise DependencyError(f"{cmd} executable not found") from exc
    except subprocess.CalledProcessError as exc:
        logger.error(exc.stderr)
        raise

    return result.stdout


class DependencyError(TinkerboxError):
    pass
