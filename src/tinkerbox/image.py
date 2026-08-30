import tinkerbox
import importlib.resources
import json
import logging
import os
import tempfile
from collections import defaultdict
from dataclasses import replace
from pathlib import Path
from pprint import pp
from typing import TextIO

from tinkerbox import config_paths, package_name
from tinkerbox.profile.file import CopyFile, File, TextFile
from tinkerbox.profile.image import ImageProfile
from tinkerbox.profile.run import Run


def build_image(profile: ImageProfile, replace=False, keep_tmp=False):
    flat_profile = profile.flatten()
    profile = flat_profile.substitute()
    pp(profile.to_object())

    with tempfile.TemporaryDirectory(
        prefix=f"{package_name()}-{profile.name or 'unnamed'}.",
        delete=(not keep_tmp),
    ) as temp_dir:
        temp_dir = Path(temp_dir)
        logging.debug(f"Using temporary directory: {temp_dir}")
        with (temp_dir / "Containerfile").open("w") as f:
            assert profile.user
            assert profile.home
            uid = os.getuid()
            gid = os.getgid()
            f.write(f"FROM {profile.from_image}\n")
            f.write("USER root\n")
            f.write(
                f"RUN groupadd --gid {gid} {profile.user} "
                f"&& useradd --create-home --uid {uid} --gid {gid} --home-dir {profile.home} {profile.user}\n"
            )

            for add in profile.add:
                write_add(add, f, temp_dir)

            if environment := {k: v for k, v in profile.environment.items() if v}:
                f.write("ENV")
                for k, v in environment.items():
                    f.write(f" {k}={v}")
                f.write("\n")

            per_user_run: defaultdict[str, list[Run]] = defaultdict(list)
            for run in profile.run:
                per_user_run[run.user].append(run)

            for run in per_user_run.get("root", []):
                write_run(run, f)

            for user, runs in per_user_run.items():
                if user in (profile.user, "root"):
                    continue
                f.write(f"USER {user}\n")
                for run in runs:
                    write_run(run, f)

            f.write(f"USER {profile.user}\n")
            for run in per_user_run.get(profile.user, []):
                write_run(run, f)

            if profile.entrypoint:
                if isinstance(profile.entrypoint, list):
                    f.write("ENTRYPOINT ")
                    json.dump(profile.entrypoint, f)
                    f.write("\n")
                else:
                    f.write(f"ENTRYPOINT {profile.entrypoint}\n")

            if profile.cmd:
                if isinstance(profile.cmd, list):
                    f.write("CMD ")
                    json.dump(profile.cmd, f)
                    f.write("\n")
                else:
                    f.write(f"CMD {profile.cmd}\n")


def write_add(add: File, file: TextIO, temp_dir: Path):
    if isinstance(add, TextFile):
        src = temp_dir / f"{Path(add.dst).name}.{hash(add.content)}"
        with src.open("w") as f:
            f.write(add.content)
        add = CopyFile(
            src=str(src.absolute()),
            dst=add.dst,
            chmod=add.chmod,
            chown=add.chown,
        )
    assert isinstance(add, CopyFile)

    if not (
        add.src.startswith("./")
        or add.src.startswith("../")
        or add.src.startswith("/")
        or add.src.startswith("http://")
        or add.src.startswith("https://")
        or add.src.startswith("git://")
    ):
        add = replace(add, src=find_file(add.src))

    opts = []
    if add.chmod:
        opts.append(f"--chmod={add.chmod}")
    if add.chmod:
        opts.append(f"--chmod={add.chmod}")
    file.write(f"ADD {' '.join(opts)} {add.src} {add.dst}\n")


def write_run(run: Run, file: TextIO):
    file.write(f"RUN {run.command}\n")


def find_file(name: str) -> str:
    path = Path(name)
    assert not path.is_absolute()

    for dir in config_paths():
        file = dir / path
        if file.is_file():
            return str(file)

    if name in ["default-bootstrap.sh", "default-entrypoint.sh"]:
        file = importlib.resources.files(tinkerbox.__package__) / path
        return str(file)

    raise FileNotFoundError(f"File not found: {name!r}")
