from tinkerbox.profile.run import Run
from tinkerbox.alias_enum import AliasEnum
from dataclasses import dataclass, field
from typing import Any, Self, cast

from tinkerbox.utils import normalize_string_list, substitute

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
class ImageOptions:
    from_image: str | None = None
    name: str | None = None
    add: list[File] = field(default_factory=list)
    run: list[Run] = field(default_factory=list)
    environment: dict[str, str] = field(default_factory=dict)
    entrypoint: list[str] | str | None = None
    cmd: list[str] | str | None = None
    override: set[ImageOverride] = field(default_factory=set)

    @classmethod
    def from_object(cls, obj: Any) -> Self:
        if not isinstance(obj, dict):
            raise TypeError("Image profile must be a dict")

        obj = {**obj}
        profile = cls()

        if from_image := obj.pop("from", None):
            if not isinstance(from_image, str):
                raise TypeError("Image's `from` field should be a string")
            profile.from_image = from_image

        if name := obj.pop("name", None):
            if not isinstance(name, str):
                raise TypeError("Image's `name` field should be a string")
            profile.name = name

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
                isinstance(x, list) for x in environment
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

        obj = {}
        if fill_unset or self.from_image:
            obj["from"] = self.from_image
        if fill_unset or self.name:
            obj["name"] = self.name
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
        merged = ImageOptions()

        merged.name = self.name
        if other.name is not None:
            merged.name = other.name

        merged.from_image = self.from_image
        if other.from_image is not None:
            merged.from_image = other.from_image

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

        return cast(Self, merged)

    def substitute(self, variables: dict[str, str]) -> Self:
        from_image = substitute(self.from_image, variables) if self.from_image else None
        name = substitute(self.name, variables) if self.name else None
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

        image = type(self)(
            from_image, name, add, run, environment, entrypoint, cmd, self.override
        )

        return image
