import logging
import shlex
import subprocess
import sys
import threading

from tinkerbox import TinkerboxError

logger = logging.getLogger(__name__)


def run_podman(*args: str) -> int:
    return run("podman", *args)


def run_podman_capture(*args: str, echo_output: bool = False) -> str:
    return run_capture("podman", *args, echo_output=echo_output)


def run(cmd: str, *args: str) -> int:
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
    except subprocess.CalledProcessError as exc:
        raise CalledProcessError(
            exc.returncode,
            command,
        )

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


class CalledProcessError(TinkerboxError):
    def __init__(
        self,
        return_code: int,
        call_args: list[str],
        output: str | None = None,
        stderr: str | None = None,
    ):
        cmd = shlex.join(call_args)
        super().__init__(
            f"Subprocess returned non zero ({return_code}) exit code: {cmd}"
        )
        self.return_code: int = return_code
        self.call_args: list[str] = call_args
        self.output: str | None = output
        self.stderr: str | None = stderr
