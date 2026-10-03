import logging
import shlex
import subprocess
import sys
import threading
from dataclasses import dataclass, field

from tinkerbox import TinkerboxError

logger = logging.getLogger(__name__)


def run_podman(*args: str):
    run("podman", *args)


def run_podman_capture(*args: str, echo_output: bool = False) -> str:
    return run_capture("podman", *args, echo_output=echo_output)


def run(cmd: str, *args: str):
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


def run_capture(cmd: str, *args: str, echo_output: bool = False) -> str:
    command = [cmd, *args]
    logger.debug("$ %s", shlex.join(command))

    try:
        proc = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
    except FileNotFoundError as exc:
        raise DependencyError(f"{cmd} executable not found") from exc

    stdout_lines = []
    stderr_lines = []

    def read_stream(stream, output, log):
        for line in stream:
            output.append(line)
            if echo_output:
                log(line)

    threads = [
        threading.Thread(
            target=read_stream,
            args=(proc.stdout, stdout_lines, sys.stdout.write),
        ),
        threading.Thread(
            target=read_stream,
            args=(proc.stderr, stderr_lines, sys.stderr.write),
        ),
    ]

    for thread in threads:
        thread.start()

    try:
        proc.wait(timeout=None)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        for thread in threads:
            thread.join()
        raise

    for thread in threads:
        thread.join()

    output = "".join(stdout_lines)
    stderr = "".join(stderr_lines)

    if proc.returncode != 0:
        raise CalledProcessError(
            proc.returncode,
            command,
            output=output,
            stderr=stderr,
        )

    return "".join(stdout_lines)


class DependencyError(TinkerboxError):
    pass


@dataclass
class CalledProcessError(TinkerboxError):
    return_code: int
    args: list[str]
    output: str | None = None
    stderr: str | None = None

    def __str__(self):
        return f"Subprocess returned non zero exit code: {self.return_code}"
