from __future__ import annotations
from tinkerbox import package_name, config_paths
from collections.abc import Iterator
import tinkerbox

import importlib.resources
import json
import logging
import os
import tomllib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, TypeVar

from tinkerbox.alias_enum import AliasEnum
from tinkerbox.utils import normalize_string_list


class ProfileKind(AliasEnum):
    CONTAINER = "container"
    IMAGE = "image"

    @classmethod
    def aliases(cls) -> dict[str, ProfileKind]:
        return {
            "c": cls.CONTAINER,
            "i": cls.IMAGE,
        }


@dataclass
class Profile(ABC):
    # Profile options
    profile_name: str | None = None
    profile_source: str | Path | None = None
    description: str | None = None
    extends: list[str] = field(default_factory=list)

    @staticmethod
    @abstractmethod
    def kind() -> ProfileKind:
        raise NotImplementedError

    @classmethod
    def from_object(cls, obj):
        if not isinstance(obj, dict):
            raise TypeError("Profile value should be a dict")

        profile = cls()

        if profile_name := obj.pop("profile_name", None):
            if not isinstance(profile_name, str):
                raise TypeError("Profile name should be a string")
            profile.profile_name = profile_name

        if profile_source := obj.pop("profile_source", None):
            if not isinstance(profile_source, str | Path):
                raise TypeError("Profile's `source` field should be a string")
            profile.profile_source = profile_source

        if description := obj.pop("description", None):
            if not isinstance(description, str):
                raise TypeError("Profile's `description` field should be a string")
            profile.description = description

        if extends := obj.pop("extends", None):
            try:
                extends = normalize_string_list(extends)
            except TypeError:
                raise TypeError(
                    "Profile's `extends` field should be either list of strings or string"
                )
            profile.extends = extends

        return profile

    def to_object(self, fill_unset=False) -> dict[str, Any]:
        obj = {}
        if fill_unset or self.profile_name:
            obj["profile_name"] = self.profile_name
        if fill_unset or self.profile_source:
            obj["profile_source"] = str(self.profile_source)
        if fill_unset or self.description:
            obj["description"] = self.description
        if fill_unset or self.extends:
            obj["extends"] = self.extends

        return obj

    def flatten(self: T) -> T:
        """
        Merges this profile over loaded profiles form the `extends` field.
        """

        visited = set()
        stack = [*self.extends]
        flat = replace(self)  # Make deep copy

        if self.profile_name:
            visited.add(self.profile_name)

        while stack:
            name = stack.pop(-1)
            if name in visited:
                continue
            visited.add(name)
            base = type(self).load(name)
            stack.extend(base.extends)
            base.extends = []
            flat = base.merge(flat)

        flat.profile_name = self.profile_name
        flat.profile_source = self.profile_source

        return flat

    def merge(self: T, other: T) -> T:
        merged = type(self)()

        merged.description = self.description
        if other.description is not None:
            merged.description = other.description

        return merged

    def variables(self) -> dict[str, str]:
        variables = {k: v for k, v in os.environ.items()}

        uid = os.getuid()
        gid = os.getgid()
        variables["UID"] = str(uid)
        variables["GID"] = str(gid)
        variables["PROFILE_NAME"] = (
            self.profile_name if self.profile_name else "unnamed"
        )

        return variables

    def substitute(self: T, variables: dict[str, str] | None = None) -> T:
        """
        Substitutes `@{VAR}` in fields.
        """

        variables = {**self.variables(), **(variables or {})}

        return replace(
            self,
            user=variables["USER"],
            home=variables["HOME"],
        )

    @classmethod
    def load(cls: type[T], name: str) -> T:
        for dir in config_paths():
            for suffix in ["json", "toml"]:
                path = dir / cls.kind().value / f"{name}.{suffix}"
                if path.is_file():
                    logging.debug('Loading %s profile form "%s"', cls.kind(), path)
                    profile = None
                    try:
                        if suffix == "json":
                            with path.open("r") as f:
                                profile = cls.from_object(json.load(f))
                        if suffix == "toml":
                            with path.open("br") as f:
                                profile = cls.from_object(tomllib.load(f))
                    except Exception as exc:
                        exc.add_note(f"Profile source: {path}")
                        raise exc
                    if profile:
                        profile.profile_name = name
                        profile.profile_source = path
                        return profile

        if name == "default":
            resource_path = (
                importlib.resources.files(tinkerbox.__package__)
                / f"{name}-{cls.kind()}.toml"
            )
            if resource_path.is_file():
                with importlib.resources.as_file(resource_path) as f:
                    logging.debug('Loading build-in %s profile "%s"', cls.kind(), name)
                    text = f.read_text()
                    profile = cls.from_object(tomllib.loads(text))
                    profile.profile_name = name
                    profile.profile_source = "built-in"
                    return profile

        raise FileNotFoundError(f"Can not find {cls.kind()} profile {name}")


T = TypeVar("T", bound=Profile)


def list_profiles(kind: ProfileKind) -> set[str]:
    profiles = {"default"}
    for dir in config_paths():
        dir = dir / kind.value
        if dir.is_dir():
            for path in dir.iterdir():
                if not path.is_file() or path.suffix not in [".json", ".toml"]:
                    continue
                name = path.with_suffix("").name
                profiles.add(name)

    return profiles
