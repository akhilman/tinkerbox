import argparse
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
    add_container_args(cmd)
    add_container_profile_args(cmd)
    cmd.set_defaults(func=create_container)

    cmd = commands.add_parser("profile", aliases=["pr"], help="manage image profile")
    tinkerbox.cli.profile.setup_argparse(cmd)


def add_container_args(parser: argparse.ArgumentParser):
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
        metavar="[USER:]COMMAND",
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
        help="override image options from profile",
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


def create_container(args: argparse.Namespace):
    setup_logging(args.debug)
    print(args)

    obj = profile_opts_from_cli_args(args)
    profile = ContainerProfile.from_object(obj)
    if args.profile:
        profile.extends = args.profile
    else:
        profile.extends = ["default"]

    tinkerbox.container.create(profile)
