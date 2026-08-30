import argparse
import json
import sys

import tinkerbox.profile
from tinkerbox.logging import setup_logging
from tinkerbox.profile import ProfileKind
from tinkerbox.profile.container import ContainerProfile
from tinkerbox.profile.image import ImageProfile


def setup_argparse(parser: argparse.ArgumentParser):
    parser.add_argument(
        "kind", choices=list(ProfileKind.all_values()), help="profile kind to show"
    )
    commands = parser.add_subparsers(
        dest="profile command",
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


def list_profiles(args: argparse.Namespace):
    setup_logging(args.debug)

    kind = ProfileKind(args.kind)
    profiles = tinkerbox.profile.list_profiles(kind)
    for name in profiles:
        sys.stdout.write(f"{name}\n")


def cat_profile(args: argparse.Namespace):
    setup_logging(args.debug)

    name = args.profile
    kind = ProfileKind(args.kind)
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
