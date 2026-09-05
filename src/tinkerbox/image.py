import importlib.resources
import json
import logging
import os
import shutil
import tempfile
from collections import defaultdict
from dataclasses import asdict
from hashlib import sha1
from pathlib import Path
from subprocess import CalledProcessError
from typing import TextIO

import tinkerbox
from tinkerbox import APP_ID, TinkerboxError, config_paths
from tinkerbox.podman import run_podman, run_podman_capture
from tinkerbox.profile.add import Add, AddFile, AddText, AddUrl
from tinkerbox.profile.image import ImageProfile
from tinkerbox.profile.run import Run


def build_image(profile: ImageProfile, keep_tmp=False):
    flat_profile = profile.flatten()
    profile = flat_profile.substitute()

    with tempfile.TemporaryDirectory(
        prefix=f"{APP_ID}.{profile.name or 'unnamed'}.",
        delete=(not keep_tmp),
    ) as temp_dir:
        temp_dir = Path(temp_dir)
        logging.debug(f"Using temporary directory: {temp_dir}")
        container_file = temp_dir / "Containerfile"
        with (container_file).open("w") as f:
            assert profile.user
            assert profile.home
            uid = os.getuid()
            f.write(f"FROM {profile.from_image}\n")
            f.write("USER root\n")

            for add in profile.add:
                if add.chown not in [profile.user, str(uid)]:
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
            for run in per_user_run.get("0", []):
                write_run(run, f)

            for user, runs in per_user_run.items():
                if user in (profile.user, str(uid), "root", "0"):
                    continue
                f.write(f"USER {user}\n")
                for run in runs:
                    write_run(run, f)

            f.write(f"USER {profile.user}:{profile.user}\n")
            f.write(f"WORKDIR {profile.home}\n")

            for add in profile.add:
                if add.chown in (profile.user, str(uid)):
                    write_add(add, f, temp_dir)

            for run in per_user_run.get(profile.user, []):
                write_run(run, f)
            for run in per_user_run.get(str(uid), []):
                write_run(run, f)

            if profile.entrypoint:
                f.write("ENTRYPOINT ")
                if isinstance(profile.entrypoint, list):
                    json.dump(profile.entrypoint, f)
                else:
                    f.write(profile.entrypoint)
                f.write("\n")

            if profile.cmd:
                f.write("CMD ")
                if isinstance(profile.cmd, list):
                    json.dump(profile.cmd, f)
                else:
                    f.write(profile.cmd)
                f.write("\n")

            profile_json = json.dumps(profile.to_object(), separators=(",", ":"))
            f.write('LABEL manager="tinkerbox"\n')
            f.write(f"LABEL {APP_ID}.manager=true\n")
            f.write(f"LABEL {APP_ID}.profile={json.dumps(profile_json)}\n")

        run_podman("build", f"--tag={profile.name}", str(temp_dir))


def write_add(add: Add, file: TextIO, temp_dir: Path):
    if isinstance(add, AddText):
        text = (
            temp_dir
            / f"{add.dst.name}.{sha1(add.content.encode()).hexdigest()}/{add.dst.name}"
        )
        text.parent.mkdir(parents=True, exist_ok=True)
        with text.open("w") as f:
            logging.debug("Writing file content to `%s`", text)
            f.write(add.content)
        src = str(text.relative_to(temp_dir))
        dst = str(add.dst)
        opts: dict[str, str | None] = {
            k: v for k, v in asdict(add).items() if k not in ("content", "dst")
        }
    elif isinstance(add, AddUrl):
        src = add.url
        dst = str(add.dst)
        opts: dict[str, str | bool | list[str] | None] = {
            k: v for k, v in asdict(add).items() if k not in ("url", "dst")
        }
    elif isinstance(add, AddFile):
        if not add.src.is_absolute():
            if add.src.exists():
                src_orig = add.src.absolute()
            else:
                src_orig = find_file(add.src)
        src_copy = (
            temp_dir
            / f"{src_orig.name}.{sha1((str(src_orig.absolute())).encode()).hexdigest()}/{src_orig.name}"
        )
        src_copy.parent.mkdir(parents=True, exist_ok=True)
        if src_orig.is_dir():
            logging.debug("Copying `%s` directory to `%s`", src_orig, src_copy)
            shutil.copytree(
                src_orig, src_copy, symlinks=True, ignore_dangling_symlinks=True
            )
        else:
            logging.debug("Copying `%s` file to `%s`", src_orig, src_copy)
            shutil.copy(src_orig, src_copy, follow_symlinks=True)
        src = str(src_copy.relative_to(temp_dir))
        dst = str(add.dst)
        opts: dict[str, str | bool | list[str] | None] = {
            k: v for k, v in asdict(add).items() if k not in ("src", "dst")
        }
    else:
        raise TypeError(f"Unexpected Add type: {type(add)}")

    file.write("ADD")
    for k, v in opts.items():
        k = k.replace("_", "-")
        match v:
            case None:
                continue
            case list(x):
                for item in x:
                    file.write(f" --{k}={item}")
                continue

            case True:
                v_str = "true"
            case False:
                v_str = "false"
            case _:
                v_str = str(v)

        file.write(f" --{k}={v_str}")

    file.write(f" {src} {dst}\n")


def write_run(run: Run, file: TextIO):
    file.write("RUN")
    for k, v in run.to_object().items():
        if k in ("command", "user"):
            continue
        if v is None:
            continue
        if isinstance(v, list):
            args = []
            for vv in v:
                assert isinstance(vv, dict)
                args.extend(f"{k}={v}" for k, v in vv.items())
            file.write(f" --{k}={','.join(args)}")
        else:
            file.write(f" --{k}={v}")

    file.write(" ")
    if isinstance(run.command, list):
        json.dump(run.command, file)
    else:
        file.write(run.command)

    file.write("\n")


def find_file(path) -> Path:
    assert not path.is_absolute()

    for dir in config_paths():
        cfg = dir / path
        if cfg.exists():
            return cfg

    if path in [Path("default-bootstrap.sh"), Path("default-entrypoint.sh")]:
        built_in = importlib.resources.files(tinkerbox.__package__) / path
        return Path(str(built_in))

    raise FileNotFoundError(f"File not found: {path!r}")


def is_exists(name: str) -> bool:
    try:
        run_podman_capture("image", "exists", name)
    except CalledProcessError as exc:
        if "Error: no such object" in exc.stderr:
            return False
        raise exc

    return True


def extract_profile(name: str) -> ImageProfile:
    try:
        profile_json = run_podman_capture(
            "inspect",
            "--format",
            '{{index .Config.Labels "io.github.akhilman.tinkerbox.profile"}}',
            name,
        ).strip()
    except CalledProcessError as exc:
        if "Error: no such object" in exc.stderr:
            raise ImageNotFoundError(name) from exc
        raise exc

    if not profile_json:
        raise NonNativeImageError(name)

    obj = json.loads(profile_json)
    obj["profile_name"] = name
    obj["profile_source"] = f"image:{name}"
    return ImageProfile.from_object(obj)


class ImageNotFoundError(TinkerboxError):
    def __init__(self, image_name: str):
        super().__init__(f"Image {image_name!r} not exists")
        self.image_name = image_name


class NonNativeImageError(TinkerboxError):
    def __init__(self, image_name: str):
        super().__init__(f"Image {image_name!r} is not tinkerbox image")
        self.image_name = image_name
