import importlib.resources
import json
import logging
import os
import shutil
import tempfile
from collections import defaultdict
from collections.abc import Iterable, Iterator
from dataclasses import asdict
from hashlib import sha1
from pathlib import Path
from typing import Any, TextIO

import tinkerbox
import tinkerbox.builtin
from tinkerbox import APP_ID, TinkerboxError, subprocess
from tinkerbox.profile.add import Add, AddFile, AddText, AddUrl, AddBuiltin
from tinkerbox.profile.image import ImageProfile
from tinkerbox.profile.run import Run
from tinkerbox.subprocess import CalledProcessError

logger = logging.getLogger(__name__)


def build_image(profile: ImageProfile, keep_tmp=False) -> str:
    """
    Returns image id.
    """
    flat_profile = profile.flatten()
    profile = flat_profile.substitute(flat_profile.variables())

    with tempfile.TemporaryDirectory(
        prefix=f"{APP_ID}.{profile.name or 'unnamed'}.",
        delete=(not keep_tmp),
    ) as temp_dir:
        temp_dir = Path(temp_dir)
        logger.debug(f"Using temporary directory: {temp_dir}")
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

            profile_json = json.dumps(profile.to_object())
            f.write(f"LABEL {APP_ID}.manager=true\n")
            f.write(f"LABEL {APP_ID}.profile={json.dumps(profile_json)}\n")

        args = []
        if profile.pull:
            args.append(f"--pull={profile.pull}")

        output = subprocess.run_podman_capture(
            "build",
            *args,
            str(temp_dir),
            echo_output=True,
        )
        image_id = output.rstrip().split("\n")[-1]

        if profile.name:
            subprocess.run_podman("image", "tag", image_id, profile.name)

        return image_id


def write_add(add: Add, file: TextIO, temp_dir: Path):
    # Handle builtin resources
    if isinstance(add, AddBuiltin):
        add = AddText(
            dst=add.dst,
            content=read_builtin(add.builtin),
            chmod=add.chmod,
            chown=add.chown,
        )

    dst = str(add.dst)
    opts: dict[str, str | bool | list[str] | None] = {
        k: v
        for k, v in asdict(add).items()
        if k not in ("content", "src", "url", "dst")
    }

    if isinstance(add, AddText):
        text = (
            temp_dir
            / f"{add.dst.name}.{sha1(add.content.encode()).hexdigest()}/{add.dst.name}"
        )
        text.parent.mkdir(parents=True, exist_ok=True)
        with text.open("w") as f:
            logger.debug("Writing file content to `%s`", text)
            f.write(add.content)
        src = str(text.relative_to(temp_dir))
    elif isinstance(add, AddUrl):
        src = add.url
    elif isinstance(add, AddFile):
        if add.src.exists():
            src = copy_file(add.src, temp_dir)
        else:
            raise FileNotFoundError(f"file not found: {add.src!r}")
    else:
        raise TypeError(f"unexpected Add type: {type(add)}")

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


def read_builtin(file_name: str) -> str:
    """
    Read built-in resource
    """

    resource = importlib.resources.files(tinkerbox.builtin.__package__).joinpath(
        file_name
    )
    if resource.is_file():
        content = resource.read_text("utf-8")
        return content

    raise FileNotFoundError(f"file not found: builtin:{file_name!r}")


def copy_file(path: Path, temp_dir: Path) -> Path:
    base_name = path.name
    temp_path = (
        temp_dir
        / f"{base_name}.{sha1(str(path.absolute()).encode('utf-8')).hexdigest()}/{base_name}"
    )
    temp_path.parent.mkdir(exist_ok=True)
    if path.is_dir():
        logger.debug("Copying `%s` directory to `%s`", path, temp_path)
        shutil.copytree(path, temp_path, symlinks=True, ignore_dangling_symlinks=True)
    else:
        logger.debug("Copying `%s` file to `%s`", path, temp_path)
        shutil.copy(path, temp_path, follow_symlinks=True)

    return temp_path.relative_to(temp_dir)


def is_exists(image: str) -> bool:
    try:
        subprocess.run_podman_capture("image", "exists", image)
    except CalledProcessError:
        return False

    return True


def extract_profile(image: str) -> ImageProfile:
    try:
        profile_json = subprocess.run_podman_capture(
            "image",
            "inspect",
            f'--format={{{{index .Config.Labels "{APP_ID}.profile"}}}}',
            image,
        ).strip()
    except CalledProcessError as exc:
        if exc.stderr and "image not known" in exc.stderr:
            raise ImageNotFoundError(image) from exc
        raise exc

    if not profile_json:
        raise NonNativeImageError(image)

    obj = json.loads(profile_json)

    if not isinstance(obj, dict):
        raise NonNativeImageError(image)

    obj["profile_name"] = image

    return ImageProfile.from_object(obj, profile_source=f"image:{image}")


def extract_user_and_group(image: str) -> tuple[str, str]:
    try:
        user_group = subprocess.run_podman_capture(
            "inspect",
            "--format={{.Config.User}}",
            image,
        ).strip()
    except CalledProcessError as exc:
        if exc.stderr and "image not known" in exc.stderr:
            raise ImageNotFoundError(image) from exc
        raise exc

    assert user_group
    assert ":" in user_group

    user, group = user_group.rsplit(":", 1)
    return (user, group)


def list_image_names() -> Iterator[str]:
    images = list_images()
    for img in images:
        if names := img.get("Names"):
            if names:
                yield names[0]
                continue

        yield img["Id"]


def list_images() -> list[dict[str, Any]]:
    images = json.loads(
        subprocess.run_podman_capture(
            "image",
            "ls",
            "--sort=repository",
            f"--filter=label={APP_ID}.manager=true",
            "--format=json",
        )
    )
    return images


def remove_images(images: Iterable[str]):
    image_list = list(images)
    logger.info("Removing images: %s", ", ".join(image_list))
    subprocess.run_podman("image", "rm", *image_list)


class ImageNotFoundError(TinkerboxError):
    def __init__(self, image: str):
        super().__init__(f"Image {image!r} not found")
        self.image = image


class NonNativeImageError(TinkerboxError):
    def __init__(self, image: str):
        super().__init__(f"Image {image!r} is not tinkerbox image")
        self.image = image
