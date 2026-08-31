import argparse

from . import profile
from . import image


def main():
    parser = argparse.ArgumentParser(
        prog="tinkerbox",
        description="Tinkerbox is a tool to manage interactive podman containers for experiments and development.",
    )

    parser.add_argument("--debug", action="store_true", help="enable debug output")

    commands = parser.add_subparsers(dest="command", required=True, title="commands")

    cmd = commands.add_parser("profile", aliases=["pr"], help="manage profiles")
    profile.setup_argparse(cmd)

    cmd = commands.add_parser("image", aliases=["im"], help="manage container images")
    image.setup_argparse(cmd)

    # Parse arguments
    args = parser.parse_args()

    args.func(args)


if __name__ == "__main__":
    main()
