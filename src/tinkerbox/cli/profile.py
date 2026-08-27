from tinkerbox.logging import setup_logging
import argparse
import json
import sys

import tinkerbox.profile


def setup_argparse(parser: argparse.ArgumentParser):
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

    profiles = tinkerbox.profile.list_profiles()
    for name in profiles:
        sys.stdout.write(f"{name}\n")


def cat_profile(args: argparse.Namespace):
    setup_logging(args.debug)

    name = args.profile
    profile = tinkerbox.profile.load_profile(name)
    if args.flatten:
        profile = profile.flatten()
    sys.stdout.write(
        json.dumps(profile.to_object(fill_unset=True), sort_keys=True, indent=2)
    )
    sys.stdout.write("\n")
