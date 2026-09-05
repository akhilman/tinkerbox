import argparse
import json
import sys

import tinkerbox.image
import tinkerbox.profile
from tinkerbox.logging import setup_logging
from tinkerbox.profile import ProfileKind
from tinkerbox.profile.container import ContainerProfile
from tinkerbox.profile.image import ImageProfile


def setup_argparse(parser: argparse.ArgumentParser):
    commands = parser.add_subparsers(
        dest="sub_command",
        required=True,
        title="profile commands",
        metavar="COMMAND",
    )
    cmd_list = commands.add_parser(
        "list", aliases=["ls"], help="list available profiles"
    )
    cmd_list.set_defaults(func=list_profiles)

    cmd_cat = commands.add_parser("cat", help="show profile")
    cmd_cat.add_argument(
        "--flatten", "-f", action="store_true", help="merge with source profiles"
    )
    cmd_cat.add_argument("profile", help="profile to show")
    cmd_cat.set_defaults(func=cat_profile)

    cmd_extract = commands.add_parser(
        "extract", help="extract profile from image or container"
    )
    cmd_extract.add_argument("source", help="source image or container")
    cmd_extract.set_defaults(func=extract_profile)


def list_profiles(args: argparse.Namespace):
    setup_logging(args.debug)

    kind = ProfileKind(args.entity)
    profiles = tinkerbox.profile.list_profiles(kind)
    for name in profiles:
        sys.stdout.write(f"{name}\n")


def cat_profile(args: argparse.Namespace):
    setup_logging(args.debug)

    name = args.profile
    kind = ProfileKind(args.entity)
    match kind:
        case ProfileKind.CONTAINER:
            profile = ContainerProfile.load(name)
        case ProfileKind.IMAGE:
            profile = ImageProfile.load(name)
        case _:
            raise ValueError(f"Unexpected profile kind: {kind}")

    if args.flatten:
        profile = profile.flatten()
    sys.stdout.write(
        json.dumps(profile.to_object(fill_unset=True), sort_keys=True, indent=2)
    )
    sys.stdout.write("\n")


def extract_profile(args: argparse.Namespace):
    setup_logging(args.debug)

    source = args.source
    kind = ProfileKind(args.entity)  # TODO: Get rid of this enum.
    match kind:
        case ProfileKind.CONTAINER:
            raise NotImplementedError
        case ProfileKind.IMAGE:
            profile = tinkerbox.image.extract_profile(source)
        case _:
            raise ValueError(f"Unexpected profile kind: {kind}")
    sys.stdout.write(
        json.dumps(profile.to_object(fill_unset=True), sort_keys=True, indent=2)
    )
    sys.stdout.write("\n")
