import argparse
import sys

from tinkerbox import TinkerboxError

from . import image


def main():
    parser = argparse.ArgumentParser(
        prog="tinkerbox",
        description="Tinkerbox is a tool to manage interactive podman containers for experiments and development.",
    )

    parser.add_argument("--debug", action="store_true", help="enable debug output")

    entity = parser.add_subparsers(dest="entity", required=True, title="entities")

    cmd = entity.add_parser("image", aliases=["im"], help="manage container images")
    image.setup_argparse(cmd)

    # Parse arguments
    args = parser.parse_args()

    try:
        args.func(args)
    except TinkerboxError as exc:
        sys.stderr.write(f"{exc}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
