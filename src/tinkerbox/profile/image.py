import os
import pwd
from dataclasses import dataclass, field, replace
from typing import Any, Self

from tinkerbox.alias_enum import AliasEnum
from tinkerbox.profile.run import Run
from tinkerbox.utils import normalize_string_list, random_string, substitute

from . import Profile, ProfileKind
from .file import File


class ImageOverride(AliasEnum):
    ALL = "all"
    RUN = "run"
    ENV = "env"
    ADD = "add"

    @classmethod
    def aliases(cls) -> dict[str, "ImageOverride"]:
        return {
            "e": ImageOverride.ENV,
            "a": ImageOverride.ADD,
            "r": ImageOverride.RUN,
        }


@dataclass
class ImageProfile(Profile):
    from_image: str | None = None
    name: str | None = None
    user: str | None = None
    home: str | None = None
    add: list[File] = field(default_factory=list)
    run: list[Run] = field(default_factory=list)
    environment: dict[str, str] = field(default_factory=dict)
    entrypoint: list[str] | str | None = None
    cmd: list[str] | str | None = None
    override: set[ImageOverride] = field(default_factory=set)

    @staticmethod
    def kind() -> ProfileKind:
        return ProfileKind.IMAGE

    @classmethod
    def from_object(cls, obj: Any) -> Self:
        if not isinstance(obj, dict):
            raise TypeError("Image profile must be a dict")

        obj = {**obj}
        profile = super().from_object(obj)

        if from_image := obj.pop("from", None):
            if not isinstance(from_image, str):
                raise TypeError("Image's `from` field should be a string")
            profile.from_image = from_image

        if name := obj.pop("name", None):
            if not isinstance(name, str):
                raise TypeError("Image's `name` field should be a string")
            profile.name = name

        if user := obj.pop("user", None):
            if not isinstance(user, str):
                raise TypeError("Image's `user` field should be a string")
            profile.user = user

        if home := obj.pop("home", None):
            if not isinstance(home, str):
                raise TypeError("Image's `home` field should be a string")
            profile.home = home

        if add := obj.pop("add", None):
            if not isinstance(add, list):
                raise TypeError("Image's `add` field must be a list of dicts")
            profile.add = [File.from_object(x) for x in add]

        if run := obj.pop("run", None):
            if not isinstance(run, list):
                raise TypeError(
                    "Image's `run` field must be a list of strings or list of dicts"
                )
            profile.run = [Run.from_object(x) for x in run]

        if environment := obj.pop("environment", obj.pop("env", None)):
            if isinstance(environment, dict) and all(
                isinstance(k, str) and isinstance(v, str)
                for (k, v) in environment.items()
            ):
                pass
            elif isinstance(environment, list) and all(
                isinstance(x, str) for x in environment
            ):
                environment: dict[str, str] = {
                    k: v for k, v in ((x.split("=", 1) + [""])[:2] for x in environment)
                }
            else:
                raise TypeError(
                    "Image's `environment` field should be a dict with string keys and values or list of strings in `KEY=VAL` format"
                )
            profile.environment = environment

        if entrypoint := obj.pop("entrypoint", None):
            if not isinstance(entrypoint, list) or not (
                all(isinstance(x, str) for x in entrypoint)
                or all(
                    isinstance(x, list) and all(isinstance(y, str) for y in x)
                    for x in entrypoint
                )
            ):
                raise TypeError(
                    "Image's `entrypoint` field must be a list of strings or list of lists of strings"
                )
            profile.entrypoint = entrypoint

        if cmd := obj.pop("cmd", None):
            if not isinstance(cmd, list) or not (
                all(isinstance(x, str) for x in cmd)
                or all(
                    isinstance(x, list) and all(isinstance(y, str) for y in x)
                    for x in cmd
                )
            ):
                raise TypeError(
                    "Image's `cmd` field must be a list of strings or list of lists of strings"
                )
            profile.cmd = cmd

        if override := obj.pop("override", None):
            try:
                override = normalize_string_list(override)
            except TypeError:
                raise TypeError(
                    "Image's `override` field should be either list of strings or string"
                )
            profile.override = {ImageOverride(o) for o in override}

        if obj:
            raise ValueError(f"Profile has unexpected fields: {', '.join(obj.keys())}")

        return profile

    def to_object(self, fill_unset=False) -> dict[str, Any]:

        obj = super().to_object(fill_unset)
        if fill_unset or self.from_image:
            obj["from"] = self.from_image
        if fill_unset or self.name:
            obj["name"] = self.name
        if fill_unset or self.user:
            obj["user"] = self.user
        if fill_unset or self.home:
            obj["home"] = self.home
        if fill_unset or self.add:
            obj["add"] = [x.to_object() for x in self.add]
        if fill_unset or self.run:
            obj["run"] = [x.to_object() for x in self.run]
        if fill_unset or self.environment:
            obj["environment"] = self.environment
        if fill_unset or self.entrypoint:
            obj["entrypoint"] = self.entrypoint
        if fill_unset or self.cmd:
            obj["cmd"] = self.cmd
        if fill_unset or self.override:
            obj["override"] = list(sorted(map(str, self.override)))

        return obj

    def merge(self, other: Self) -> Self:
        merged = super().merge(other)

        merged.name = self.name
        if other.name is not None:
            merged.name = other.name

        merged.from_image = self.from_image
        if other.from_image is not None:
            merged.from_image = other.from_image

        merged.user = self.user
        if other.user is not None:
            merged.user = other.user

        merged.home = self.home
        if other.home is not None:
            merged.home = other.home

        if not other.override & {ImageOverride.ADD, ImageOverride.ALL}:
            merged.add.extend(self.add)
        merged.add.extend(other.add)

        if not other.override & {ImageOverride.ENV, ImageOverride.ALL}:
            merged.environment.update(**self.environment)
        merged.environment.update(**other.environment)

        if not other.override & {ImageOverride.RUN, ImageOverride.ALL}:
            merged.run.extend(self.run)
        merged.run.extend(other.run)

        merged.entrypoint = self.entrypoint
        if other.entrypoint is not None:
            merged.entrypoint = other.entrypoint

        merged.cmd = self.cmd
        if other.cmd is not None:
            merged.cmd = other.cmd

        merged.override = self.override | other.override

        return merged

    def variables(self) -> dict[str, str]:
        variables = super().variables()
        uid = os.getuid()
        user = self.user or pwd.getpwuid(uid).pw_name
        variables["IMAGE_NAME"] = (
            substitute(self.name, variables)
            if self.name
            else variables["PROFILE_NAME"] + random_string()
        )
        variables["CONTAINER_USER"] = user
        home = substitute(self.home or pwd.getpwuid(uid).pw_dir, variables)
        variables["CONTAINER_HOME"] = home
        return variables

    def substitute(self, variables: dict[str, str] | None = None) -> Self:
        variables = {**self.variables(), **(variables or {})}

        from_image = substitute(self.from_image, variables) if self.from_image else None
        name = variables["IMAGE_NAME"]
        user = variables["USER"]
        home = variables["HOME"]
        add = [x.substitute(variables) for x in self.add]
        run = [x.substitute(variables) for x in self.run]
        environment = {k: substitute(v, variables) for k, v in self.environment.items()}

        if isinstance(self.entrypoint, list):
            entrypoint = [substitute(x, variables) for x in self.entrypoint]
        elif isinstance(self.entrypoint, str):
            entrypoint = substitute(self.entrypoint, variables)
        else:
            entrypoint = None

        if isinstance(self.cmd, list):
            cmd = [substitute(x, variables) for x in self.cmd]
        elif isinstance(self.cmd, str):
            cmd = substitute(self.cmd, variables)
        else:
            cmd = None

        return replace(
            super().substitute(variables=variables),
            from_image=from_image,
            name=name,
            user=user,
            home=home,
            add=add,
            run=run,
            environment=environment,
            entrypoint=entrypoint,
            cmd=cmd,
        )
