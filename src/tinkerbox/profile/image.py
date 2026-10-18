import os
import pwd
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Self

from tinkerbox.alias_enum import AliasEnum
from tinkerbox.profile.run import Run
from tinkerbox.utils import substitute

from . import (
    Profile,
    ProfileKind,
    UnexpectedFieldsError,
    parse_enum_set,
    parse_object_list,
    parse_enum,
    parse_string,
    parse_string_map,
    parse_string_or_string_list,
)
from .add import Add


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


class PullPolicy(AliasEnum):
    ALWAYS = "always"
    MISSING = "missing"
    NEVER = "never"
    NEWER = "newer"

    @classmethod
    def aliases(cls) -> dict[str, "PullPolicy"]:
        return {
            "a": PullPolicy.ALWAYS,
            "m": PullPolicy.MISSING,
            "n": PullPolicy.NEVER,
            "update": PullPolicy.NEWER,
            "u": PullPolicy.NEWER,
        }


@dataclass
class ImageProfile(Profile):
    from_image: str | None = None
    pull: PullPolicy | None = None
    name: str | None = None
    user: str | None = None
    home: str | None = None
    add: list[Add] = field(default_factory=list)
    run: list[Run] = field(default_factory=list)
    environment: dict[str, str] = field(default_factory=dict)
    entrypoint: list[str] | str | None = None
    cmd: list[str] | str | None = None
    override: set[ImageOverride] = field(default_factory=set)

    @staticmethod
    def kind() -> ProfileKind:
        return ProfileKind.IMAGE

    @classmethod
    def from_object(
        cls, obj: dict[str, Any], profile_source: str | Path | None = None
    ) -> Self:

        obj = {**obj}
        profile = super().from_object(obj, profile_source=profile_source)

        if from_image := obj.pop("from", None):
            profile.from_image = parse_string(
                from_image,
                cls,
                "from_image",
                profile_source,
            )

        if pull := obj.pop("pull", None):
            profile.pull = parse_enum(
                pull,
                PullPolicy,
                cls,
                "pull",
                profile_source,
            )

        if name := obj.pop("name", None):
            profile.name = parse_string(
                name,
                cls,
                "name",
                profile_source,
            )

        if user := obj.pop("user", None):
            profile.user = parse_string(
                user,
                cls,
                "user",
                profile_source,
            )

        if home := obj.pop("home", None):
            profile.home = parse_string(
                home,
                cls,
                "home",
                profile_source,
            )

        if add := obj.pop("add", None):
            profile.add = parse_object_list(
                add,
                Add.from_object,
                cls,
                "add",
                profile_source,
            )

        if run := obj.pop("run", None):
            profile.run = parse_object_list(
                run,
                Run.from_object,
                cls,
                "run",
                profile_source,
            )

        if environment := obj.pop("environment", obj.pop("env", None)):
            profile.environment = parse_string_map(
                environment,
                cls,
                "environment",
                profile_source,
            )

        if entrypoint := obj.pop("entrypoint", None):
            profile.entrypoint = parse_string_or_string_list(
                entrypoint,
                cls,
                "entrypoint",
                profile_source,
            )

        if cmd := obj.pop("cmd", None):
            profile.cmd = parse_string_or_string_list(
                cmd,
                cls,
                "cmd",
                profile_source,
            )

        if override := obj.pop("override", None):
            profile.override = parse_enum_set(
                override,
                ImageOverride,
                cls,
                "override",
                profile_source,
            )

        if obj:
            raise UnexpectedFieldsError(
                fields=list(obj.keys()),
                cls=cls,
                source=profile_source,
            )

        return profile

    def to_object(self, fill_unset=False) -> dict[str, Any]:

        obj = super().to_object(fill_unset)
        if fill_unset or self.from_image:
            obj["from"] = self.from_image
        if fill_unset or self.pull:
            obj["pull"] = self.pull
        if fill_unset or self.name:
            obj["name"] = self.name
        if fill_unset or self.user:
            obj["user"] = self.user
        if fill_unset or self.home:
            obj["home"] = self.home
        if fill_unset or self.add:
            obj["add"] = [x.to_object(fill_unset=fill_unset) for x in self.add]
        if fill_unset or self.run:
            obj["run"] = [x.to_object(fill_unset=fill_unset) for x in self.run]
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

        merged.pull = self.pull
        if other.pull is not None:
            merged.pull = other.pull

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
        if self.name:
            variables["IMAGE_NAME"] = substitute(self.name, variables)
        variables["CONTAINER_USER"] = user
        home = substitute(self.home or pwd.getpwuid(uid).pw_dir, variables)
        variables["CONTAINER_HOME"] = home
        return variables

    def substitute(self, variables: dict[str, str] | None = None) -> Self:
        variables = {**self.variables(), **(variables or {})}

        from_image = substitute(self.from_image, variables) if self.from_image else None
        name = variables.get("IMAGE_NAME", self.name)
        user = variables["CONTAINER_USER"]
        home = variables["CONTAINER_HOME"]
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
            self,
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
