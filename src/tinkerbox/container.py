import json
import logging
import os
import re
import shlex
import stat
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import tinkerbox.image
from tinkerbox import APP_ID, TinkerboxError, subprocess
from tinkerbox.profile.container import ContainerProfile, Passthrough
from tinkerbox.profile.device import Device, DevicePermission
from tinkerbox.profile.exec import Exec
from tinkerbox.profile.mount import Mount
from tinkerbox.subprocess import CalledProcessError, run_podman

logger = logging.getLogger(__name__)


def create(profile: ContainerProfile) -> str:
    """
    Returns container id.
    """
    flat_profile = profile.flatten()

    image = flat_profile.image

    if not image:
        raise ImageNotSpecifiedError

    image_profile = tinkerbox.image.extract_profile(image)
    profile = flat_profile.substitute(
        {**image_profile.variables(), **flat_profile.variables()}
    )

    if profile.name and is_exists(profile.name):
        raise ContainerExistsError(profile.name)

    logger.info("Creating container from image %s", profile.image)

    args = []

    if profile.passthrough:
        profile = apply_passthrough(profile)

    if profile.name:
        args.append(f"--hostname={profile.name}")

    user, group = tinkerbox.image.extract_user_and_group(image)
    args.append(f"--user={user}:{group}")

    # Keep user and group ids.
    args.append("--userns=keep-id")
    args.append("--group-add=keep-groups")

    # Bypass SELinux restrictions on Fedora host.
    args.append("--security-opt=label=type:container_runtime_t")

    for k, v in profile.environment.items():
        args.append(f"--env={k}={v}")

    for dev in profile.devices:
        args.append(f"--device={dev.to_argument()}")

    for mnt in profile.mounts:
        args.append(f"--mount={mnt.to_argument()}")

    for vol in profile.volumes:
        args.append(f"--volume={vol.to_argument()}")

    for net in profile.networks:
        args.append(f"--network={net.to_argument()}")

    for pub in profile.publish:
        args.append(f"--publish={pub.to_argument()}")

    profile_json = json.dumps(flat_profile.to_object())
    args.append(f"--label={APP_ID}.manager=true")
    args.append(f"--label={APP_ID}.profile={profile_json}")

    container_id = subprocess.run_podman_capture("run", "-d", *args, image)
    container_id = container_id.strip()

    try:
        for cp in profile.copy:
            src = cp.src.expanduser()
            dst = cp.dst.expanduser() if cp.dst else src

            if cp.src_container:
                src = f"{cp.src_container}:{src}"
            else:
                src = str(src)

            dst = f"{container_id}:{dst}"

            if cp.ignore_failure:
                logger.info(f"Trying to copy: {cp.src} -> {cp.dst}")
            else:
                logger.info(f"Copying: {cp.src} -> {cp.dst}")

            try:
                subprocess.run_podman("container", "cp", src, dst)
            except CalledProcessError:
                if cp.ignore_failure:
                    logger.warning("Failed to copy file from `%s` to `%s`", src, dst)
                else:
                    raise

        pass_env_args = [f"--env={env}" for env in profile.pass_environment]

        for exec in profile.exec:
            if isinstance(exec.command, list):
                command = exec.command
            else:
                command = shlex.split(exec.command)

            args = []
            if exec.user:
                args.append(f"--user={exec.user}")
            if exec.work_dir:
                args.append(f"--workdir={exec.work_dir}")

            msg = "Trying to execute" if exec.ignore_failure else "Executing"
            if exec.user:
                msg = f"{msg} as {exec.user}"
            if exec.work_dir:
                msg = f"{msg} in {exec.work_dir}"
            logger.info("%s: %s", msg, shlex.join(command))

            try:
                subprocess.run_podman(
                    "container",
                    "exec",
                    *args,
                    *pass_env_args,
                    container_id,
                    *command,
                )
            except CalledProcessError:
                if exec.ignore_failure:
                    logger.warning(
                        "Failed to execute `%s` in the container", shlex.join(command)
                    )
                else:
                    raise

        if name := profile.name:
            run_podman("container", "rename", container_id, name)
    except:
        stop(container_id)
        remove(container_id)
        raise

    return container_id


def enter(container: str, command: str | None = None, user: str | None = None):
    logger.debug(f"Entering container: {container}")

    profile = extract_profile(container)
    args = []

    if command:
        pass
    elif profile.enter_command:
        command = profile.enter_command
    else:
        command = "sh"
    cmd_args = shlex.split(command)

    if user:
        args.append(f"--user={user}")

    for env in profile.pass_environment:
        args.append(f"--env={env}")

    start(container)
    subprocess.run_podman("container", "exec", "-it", *args, container, *cmd_args)


def start(containers: str | list[str]):
    if isinstance(containers, str):
        containers = [containers]
    logger.debug(f"Stating container: {' '.join(containers)}")
    subprocess.run_podman_capture("container", "start", *containers)


def stop(containers: str | list[str]):
    if isinstance(containers, str):
        containers = [containers]
    logger.debug(f"Stopping containers: {' '.join(containers)}")
    subprocess.run_podman_capture("container", "stop", *containers)


def remove(containers: str | list[str]):
    if isinstance(containers, str):
        containers = [containers]
    logger.debug(f"Removing containers: {' '.join(containers)}")
    subprocess.run_podman_capture("container", "rm", *containers)


def is_exists(container: str) -> bool:
    try:
        subprocess.run_podman("container", "exists", container)
    except CalledProcessError:
        return False

    return True


def is_running(container: str) -> bool:
    try:
        output = subprocess.run_podman_capture(
            "container",
            "inspect",
            "--format='{{.State.Running}}'",
            container,
        )

    except CalledProcessError as exc:
        if exc.stderr and "no such container" in exc.stderr:
            raise ContainerNotFoundError(container)
        raise
    return "true" in output


def is_paused(container: str) -> bool:
    running = subprocess.run_podman_capture(
        "podman",
        "container",
        "inspect",
        "--format='{{.State.Paused}}'",
        container,
    ).strip()
    return running == "true"


def apply_passthrough(profile: ContainerProfile) -> ContainerProfile:
    passthrough = profile.passthrough
    pass_profile = ContainerProfile()

    if runtime_dir_env := os.getenv("XDG_RUNTIME_DIR"):
        xdg_runtime_dir = Path(runtime_dir_env)
    else:
        raise XdgRuntimeDirNotSetError

    if passthrough & {Passthrough.ALL, Passthrough.PULSEAUDIO}:
        pulse_dir = Path(xdg_runtime_dir) / "pulse"
        if not pulse_dir.is_dir():
            raise PassthroughError(Passthrough.PULSEAUDIO, f"{pulse_dir} is not exists")
        pass_profile.mounts.append(
            Mount(
                mount_type="bind",
                options={
                    "src": str(pulse_dir),
                    "dst": str(pulse_dir),
                },
            )
        )

    if passthrough & {Passthrough.ALL, Passthrough.PIPEWIRE}:
        pw_cli_output = subprocess.run_capture("pw-cli", "ls")
        match = re.search(
            r'PipeWire:Interface:Core.*?core\.name\s*=\s*"([^"]+)"',
            pw_cli_output,
            re.DOTALL,
        )
        socket_name = match.group(1) if match else None
        if not socket_name:
            raise PassthroughError(Passthrough.PIPEWIRE, "Can not find pipewire socket")
        pw_socket = xdg_runtime_dir / socket_name
        if not (xdg_runtime_dir / socket_name).is_socket():
            raise PassthroughError(
                Passthrough.PIPEWIRE, f"Pipewire socket not exists {pw_socket}"
            )
        pass_profile.mounts.append(
            Mount(
                mount_type="bind",
                options={
                    "src": str(pw_socket),
                    "dst": str(pw_socket),
                },
            )
        )

    if passthrough & {Passthrough.ALL, Passthrough.DBUS}:
        bus_socket = xdg_runtime_dir / "bus"
        if not bus_socket.is_socket():
            PassthroughError(Passthrough.DBUS, f"DBus socket not exists {bus_socket}")
        pass_profile.mounts.append(
            Mount(
                mount_type="bind",
                options={
                    "src": str(bus_socket),
                    "dst": str(bus_socket),
                },
            )
        )

    if passthrough & {Passthrough.ALL, Passthrough.WAYLAND}:
        wayland_env = os.getenv("WAYLAND_DISPLAY")
        if not wayland_env:
            raise PassthroughError(
                Passthrough.WAYLAND, "Environment variable `WAYLAND_DISPLAY` is not set"
            )
        wayland_socket = xdg_runtime_dir / wayland_env
        if not wayland_socket.is_socket():
            raise PassthroughError(
                Passthrough.WAYLAND, f"Wayland socket not exists {wayland_socket}"
            )
        pass_profile.mounts.append(
            Mount(
                mount_type="bind",
                options={
                    "src": str(wayland_socket),
                    "dst": str(wayland_socket),
                },
            )
        )
        pass_profile.environment["WAYLAND_DISPLAY"] = wayland_env

    if passthrough & {Passthrough.ALL, Passthrough.X11}:
        x11_dir = Path("/tmp/.X11-unix")
        if not x11_dir.is_dir():
            raise PassthroughError(
                Passthrough.X11, f"X11 socket directory not exists {x11_dir}"
            )
        pass_profile.mounts.append(
            Mount(
                mount_type="bind",
                options={
                    "src": str(x11_dir),
                    "dst": str(x11_dir),
                },
            )
        )
        if x11_display := os.getenv("DISPLAY"):
            pass_profile.environment["DISPLAY"] = x11_display

    if passthrough & {Passthrough.ALL, Passthrough.GPU}:
        for entry in Path("/dev/dri").rglob("*"):
            mode = entry.lstat().st_mode

            if stat.S_ISCHR(mode):
                pass_profile.devices.append(
                    Device(
                        str(entry),
                        str(entry),
                        {DevicePermission.READ, DevicePermission.WRITE},
                    )
                )
            elif stat.S_ISLNK(mode):
                pass_profile.exec.append(
                    Exec(
                        ["mkdir", "-p", str(entry.parent)],
                        user="root",
                    )
                )
                pass_profile.exec.append(
                    Exec(
                        ["ln", "-s", str(entry.readlink()), str(entry)],
                        user="root",
                    )
                )
    pass_profile = pass_profile.merge(profile)

    return pass_profile


def extract_profile(container: str) -> ContainerProfile:
    try:
        profile_json = subprocess.run_podman_capture(
            "container",
            "inspect",
            f'--format={{{{index .Config.Labels "{APP_ID}.profile"}}}}',
            container,
        ).strip()
    except CalledProcessError as exc:
        if exc.stderr and "Error: no such container" in exc.stderr:
            raise ContainerNotFoundError(container) from exc
        raise

    if not profile_json:
        raise NonNativeContainerError(container)

    obj = json.loads(profile_json)
    if not isinstance(obj, dict):
        raise NonNativeContainerError(container)

    obj["profile_name"] = container

    return ContainerProfile.from_object(obj, profile_source=f"container:{container}")


def list_containers(calculate_size: bool = False) -> list[dict[str, Any]]:
    args = ["--size"] if calculate_size else []
    images = json.loads(
        subprocess.run_podman_capture(
            "container",
            "ls",
            "--all",
            "--sort=names",
            f"--filter=label={APP_ID}.manager=true",
            "--format=json",
            *args,
        )
    )
    return images


def list_container_names() -> Iterator[str]:
    images = list_containers()
    for img in images:
        if (names := img.get("Names")) and names:
            yield names[0]
            continue

        yield img["Id"]


class ContainerExistsError(TinkerboxError):
    def __init__(self, container: str):
        super().__init__(f"Container {container!r} already exists")
        self.container = container


class ContainerNotFoundError(TinkerboxError):
    def __init__(self, container: str):
        super().__init__(f"Container {container!r} not exists")
        self.container = container


class NonNativeContainerError(TinkerboxError):
    def __init__(self, container: str):
        super().__init__(f"Container {container!r} is not tinkerbox container")
        self.container = container


class ImageNotSpecifiedError(TinkerboxError):
    def __init__(self):
        super().__init__("Image not specified")


class XdgRuntimeDirNotSetError(TinkerboxError):
    def __init__(self):
        super().__init__("Environment variable XDG_RUNTIME_DIR is not set")


class PassthroughError(TinkerboxError):
    def __init__(self, passthrough: Passthrough, message=""):
        msg = f"Failed to initialize ${passthrough} passthrough"
        if message:
            msg += ": ${message}"
        super().__init__(msg)
