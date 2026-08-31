import logging
import shlex
import subprocess

logger = logging.getLogger(__name__)


def run_podman(*args: str):
    """
    raises subprocess.CalledProcessError on non-zero exit
    """
    command = ["podman", *args]
    logger.debug("$ %s", shlex.join(command))

    subprocess.run(
        command,
        text=True,
        check=True,
    )


def run_podman_capture(*args: str) -> str:
    """
    raises subprocess.CalledProcessError on non-zero exit
    """
    command = ["podman", *args]
    logger.debug("$ %s", shlex.join(command))

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        text=True,
        check=True,
    )

    return result.stdout
