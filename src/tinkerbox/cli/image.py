from typing import Any
import argparse

import tinkerbox.image
import tinkerbox.cli.profile
from tinkerbox.logging import setup_logging
from tinkerbox.profile.image import ImageOverride, ImageProfile


def setup_argparse(parser: argparse.ArgumentParser):
    commands = parser.add_subparsers(
        dest="command",
        required=True,
        title="image commands",
        metavar="COMMAND",
    )

    cmd = commands.add_parser("list", aliases=["ls"], help="list images")
    cmd.set_defaults(func=list_images)

    cmd = commands.add_parser(
        "build", aliases=["bd"], help="build an image from profile"
    )
    cmd.add_argument("--keep-tmp", action="store_true", help="keep temporary files")
    add_image_args(cmd)
    cmd.set_defaults(func=build_image)

    cmd = commands.add_parser("profile", aliases=["pr"], help="manage image profile")
    tinkerbox.cli.profile.setup_argparse(cmd)


def add_image_args(parser: argparse.ArgumentParser):
    parser.add_argument("--from", "-f", help="base image")
    parser.add_argument("name", help="image name")
    parser.add_argument("profile", nargs="*", help="profile to use")
    add_update_image_args(parser)


def add_update_image_args(parser: argparse.ArgumentParser):
    parser.add_argument("--user", "-u", help="user name (host user name by default)")
    parser.add_argument(
        "--home", help="set user's home directory (same as host's by default)"
    )
    parser.add_argument(
        "--add",
        "-a",
        action="append",
        help="add file to the image",
        metavar="[HOST-PATH|RESOURCE-NAME|URL:]CONTAINER-PATH[:[chown=USER,][chmod=MODE]]",
    )
    parser.add_argument(
        "--run",
        "-r",
        action="append",
        help="run command inside the image",
        metavar="[USER:]COMMAND",
    )
    parser.add_argument(
        "--env",
        "-e",
        action="append",
        help="set environment variable",
        metavar="KEY=VAL",
    )
    parser.add_argument("--entrypoint", help="set the image entry point")
    parser.add_argument("--cmd", help="set the image command")
    parser.add_argument(
        "--override",
        metavar="{" + ",".join(ImageOverride.all_values()) + "}",
        action="append",
        help="override image options from profile",
    )


def profile_from_update_image_args(args: argparse.Namespace) -> ImageProfile:
    update_image_args = [
        "from",
        "name",
        "user",
        "home",
        "add",
        "run",
        "env",
        "entrypoint",
        "cmd",
        "override",
    ]
    image_options = {k: v for k, v in vars(args).items() if k in update_image_args}
    profile = ImageProfile.from_object(image_options)
    return profile


def list_images(args: argparse.Namespace):
    setup_logging(args.debug)

    print("list_images")
    print(args)


def build_image(args: argparse.Namespace):
    setup_logging(args.debug)
    print(args)

    profile = profile_from_update_image_args(args)
    if args.profile:
        profile.extends = args.profile
    else:
        profile.extends = ["default"]

    tinkerbox.image.build_image(profile, keep_tmp=args.keep_tmp)


def cat_image_profile(args: argparse.Namespace):
    setup_logging(args.debug)

    print("image_profile")
    print(args)


def remove_image(args: argparse.Namespace):
    setup_logging(args.debug)

    print("remove_image")
    print(args)


def rename_image(args: argparse.Namespace):
    setup_logging(args.debug)

    print("rename_image")
    print(args)
