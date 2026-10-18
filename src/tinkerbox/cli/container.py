from tinkerbox import TinkerboxError
import argparse
import sys
from typing import Any

import tinkerbox.cli.profile
import tinkerbox.container
from tinkerbox.logging import setup_logging
from tinkerbox.profile.container import (
    ContainerOverride,
    ContainerProfile,
    Passthrough,
)


def setup_argparse(parser: argparse.ArgumentParser):
    commands = parser.add_subparsers(
        dest="command",
        required=True,
        title="container commands",
        metavar="COMMAND",
    )

    cmd = commands.add_parser(
        "create", aliases=["cr"], help="create a new container from an image"
    )
    add_cerate_args(cmd)
    add_container_profile_args(cmd)
    cmd.set_defaults(func=create_container)

    cmd = commands.add_parser("enter", aliases=["en"], help="enter to the container")
    add_enter_args(cmd)
    cmd.set_defaults(func=enter_container)

    cmd = commands.add_parser("list", aliases=["ls"], help="list containers")
    cmd.set_defaults(func=list_containers)

    cmd = commands.add_parser(
        "profile",
        aliases=["pr"],
        help="manage container profiles",
    )
    tinkerbox.cli.profile.setup_argparse(cmd)

    cmd = commands.add_parser(
        "remove",
        aliases=["rm"],
        help="remove one or more containers",
    )
    cmd.add_argument(
        "--stop",
        "-s",
        action="store_true",
        help="stop running containers",
    )
    cmd.add_argument("container", nargs="+", help="container to remove")
    cmd.set_defaults(func=remove_containers)

    cmd = commands.add_parser(
        "start", aliases=["st"], help="start one or more containers"
    )
    cmd.add_argument("container", nargs="+", help="container to start")
    cmd.set_defaults(func=start_containers)

    cmd = commands.add_parser(
        "stop", aliases=["sp"], help="stop one or more containers"
    )
    cmd.add_argument("container", nargs="+", help="container to stop")
    cmd.set_defaults(func=stop_containers)


def add_cerate_args(parser: argparse.ArgumentParser):
    parser.add_argument(
        "--enter",
        "-E",
        action="store_true",
        help="enter to the newly created container",
    )
    parser.add_argument("image", help="image name")
    parser.add_argument("name", help="container name")
    parser.add_argument("profile", nargs="*", help="profile to use")


def add_container_profile_args(parser: argparse.ArgumentParser):
    parser.add_argument(
        "--passthrough",
        "-P",
        metavar="{" + ",".join(Passthrough.all_values()) + "}",
        action="append",
        help="passthrough host services",
    )
    parser.add_argument(
        "--copy",
        "-C",
        action="append",
        help="copy files to the container, DST takes precedence as the destination",
        metavar="[SRC_CONTAINER:]SRC[:DST]",
    )
    parser.add_argument(
        "--device",
        "-d",
        dest="devices",
        action="append",
        help="add a host device to the container",
        metavar="HOST-DEVICE[:CONTAINER-DEVICE][:PERMISSIONS]",
    )
    parser.add_argument(
        "--env",
        "-e",
        action="append",
        help="set environment variable",
        metavar="KEY=VAL",
    )
    parser.add_argument(
        "--exec",
        "-x",
        action="append",
        help="execute a command inside the container",
        metavar="[USER:[WORKDIR:]]COMMAND",
    )
    parser.add_argument(
        "--mount",
        "-m",
        dest="mounts",
        action="append",
        help="attach a filesystem mount to the container",
        metavar="(type=TYPE,|TYPE:)TYPE-SPECIFIC-OPTION[,...]",
    )
    parser.add_argument(
        "--volume",
        "-v",
        dest="devices",
        action="append",
        help="create a bind mount to the volume or directory",
        metavar="[[SOURCE-VOLUME|HOST-DIR:]CONTAINER-DIR[:OPTIONS]]",
    )
    parser.add_argument(
        "--network",
        "-n",
        dest="networks",
        action="append",
        help="add  a  network-scoped  alias  for the container",
        metavar="MODE:MODE-SPECIFIC-OPTION[,...]",
    )
    parser.add_argument(
        "--publish",
        "-p",
        action="append",
        help="publish a container's port, or range of ports, to the host",
        metavar="[[IP:][HOSTPORT]:]CONTAINER_PORT[/PROTOCOL]",
    )
    parser.add_argument(
        "--override",
        metavar="{" + ",".join(ContainerOverride.all_values()) + "}",
        action="append",
        help="override inherited configuration for the specified options, replacing rather than merging lists, sets and maps",
    )


def profile_opts_from_cli_args(args: argparse.Namespace) -> dict[str, Any]:
    update_image_args = [
        "image",
        "name",
        "extends",
        "passthrough",
        "copy",
        "devices",
        "env",
        "exec",
        "mounts",
        "volumes",
        "networks",
        "publish",
        "override",
    ]
    return {k: v for k, v in vars(args).items() if k in update_image_args}


def list_containers(args: argparse.Namespace):
    setup_logging(args.debug)

    for name in tinkerbox.container.list_containers():
        sys.stdout.write(f"{name}\n")


def create_container(args: argparse.Namespace):
    setup_logging(args.debug)

    obj = profile_opts_from_cli_args(args)
    profile = ContainerProfile.from_object(obj, profile_source="command line")
    if args.profile:
        profile.extends = args.profile
    else:
        profile.extends = ["default"]

    container_id = tinkerbox.container.create(profile)

    if args.enter:
        tinkerbox.container.enter(container_id)
    else:
        tinkerbox.container.stop(container_id)


def add_enter_args(parser: argparse.ArgumentParser):
    parser.add_argument("--command", "-c", help="command to run")
    parser.add_argument("--user", "-u", help="set user or UID to use")
    parser.add_argument("container", help="container to enter")


def enter_container(args: argparse.Namespace):
    setup_logging(args.debug)
    tinkerbox.container.enter(args.container, command=args.command, user=args.user)


def remove_containers(args: argparse.Namespace):
    setup_logging(args.debug)

    if args.stop:
        tinkerbox.container.stop(args.container)
    else:
        for container in args.container:
            if tinkerbox.container.is_running(container):
                raise TinkerboxError(f"container `{container}` is running")

    tinkerbox.container.remove(args.container)


def start_containers(args: argparse.Namespace):
    setup_logging(args.debug)
    tinkerbox.container.start(args.container)


def stop_containers(args: argparse.Namespace):
    setup_logging(args.debug)
    tinkerbox.container.stop(args.container)
