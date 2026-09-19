import shlex
from tinkerbox.profile.device import Device, DevicePermission
from tinkerbox.profile.exec import Exec
import stat
import json
import re
import os
from dataclasses import replace
from pathlib import Path
from pprint import pp
from subprocess import CalledProcessError

import tinkerbox.image
from tinkerbox import TinkerboxError, shell, APP_ID
from tinkerbox.profile.container import Passthrough, ContainerProfile, ContainerOverride
from tinkerbox.profile.mount import Mount


def create(profile: ContainerProfile):
    flat_profile = profile.flatten()

    image = flat_profile.image

    if not image:
        raise ImageNotSpecifiedError

    image_profile = tinkerbox.image.extract_profile(image)
    profile = flat_profile.substitute(image_profile.variables())
    args = []

    if profile.passthrough:
        profile = apply_passthrough(profile)

    if profile.name:
        args.append(f"--name={profile.name}")
        args.append(f"--hostname={profile.name}")

    user, group = tinkerbox.image.extract_user_and_group(image)
    args.append(f"--user={user}:{group}")

    # Keep user and group ids.
    args.append("--userns=keep-id")
    args.append("--group-add=keep-groups")

    profile_json = json.dumps(profile.to_object(), separators=(",", ":"))
    args.append('--label=manager="tinkerbox"')
    args.append(f"--label={APP_ID}.manager=true")
    args.append(f"--label={APP_ID}.profile={json.dumps(profile_json)}")

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

    container_id = shell.run_podman_capture(
        "run",
        "-d",
        *args,
        image,
    )
    container_id = container_id.strip()

    for cp in profile.copy:
        if cp.src_container:
            src = f"{cp.src_container}:{cp.src}"
        else:
            src = str(cp.src.expanduser())

        if cp.dst:
            dst = cp.dst
        else:
            dst = cp.src
        dst = f"{container_id}:{dst}"
        shell.run_podman("container", "cp", src, dst)

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

        shell.run_podman("container", "exec", *args, container_id, *command)


def apply_passthrough(profile: ContainerProfile) -> ContainerProfile:
    passtrhough = profile.passthrough
    pass_profile = ContainerProfile()

    if runtime_dir_env := os.getenv("XDG_RUNTIME_DIR"):
        xdg_runtime_dir = Path(runtime_dir_env)
    else:
        raise XdgRuntimeDirNotSetError

    if passtrhough & {Passthrough.ALL, Passthrough.PULSEAUDIO}:
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

    if passtrhough & {Passthrough.ALL, Passthrough.PIPEWIRE}:
        pw_cli_output = shell.run_capture("pw-cli", "ls")
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

    if passtrhough & {Passthrough.ALL, Passthrough.DBUS}:
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

    if passtrhough & {Passthrough.ALL, Passthrough.WAYLAND}:
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

    if passtrhough & {Passthrough.ALL, Passthrough.X11}:
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

    if passtrhough & {Passthrough.ALL, Passthrough.GPU}:
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


def is_exists(name: str) -> bool:
    try:
        shell.run_podman("container", "exists", name)
    except CalledProcessError:
        return False

    return True


def extract_profile(container: str) -> ContainerProfile:
    raise NotImplementedError


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
