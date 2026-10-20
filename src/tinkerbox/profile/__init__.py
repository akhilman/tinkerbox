from __future__ import annotations

import importlib.resources
import itertools
import json
import logging
import os
import tomllib
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, TypeVar

import tinkerbox
import tinkerbox.builtin
import tinkerbox.utils
from tinkerbox import TinkerboxError, config_paths
from tinkerbox.alias_enum import AliasEnum


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
    def from_object(cls, obj: dict[str, Any], profile_source: str | Path | None = None):

        profile = cls()

        profile.profile_source = profile_source

        if profile_name := obj.pop("profile_name", None):
            profile.profile_name = parse_string(
                profile_name,
                cls,
                "profile_name",
                profile_source,
            )
        if description := obj.pop("description", None):
            profile.description = parse_string(
                description,
                cls,
                "description",
                profile_source,
            )

        if extends := obj.pop("extends", None):
            profile.extends = parse_string_list(
                extends,
                cls,
                "extends",
                profile_source,
            )

        return profile

    def to_object(self, fill_unset=False) -> dict[str, Any]:
        obj = {}
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

        if tz := tinkerbox.utils.timezone():
            variables["TZ"] = tz

        return variables

    @abstractmethod
    def substitute(self: T, variables: dict[str, str] | None = None) -> T:
        """
        Substitutes `@{VAR}` in fields.
        """
        _ = variables
        raise NotImplementedError

    @classmethod
    def load(cls: type[T], name: str) -> T:
        for dir in config_paths():
            for suffix in ["json", "toml"]:
                path = dir / cls.kind().value / f"{name}.{suffix}"
                if path.is_file():
                    logging.debug('Loading %s profile form "%s"', cls.kind(), path)
                    obj = None
                    try:
                        if suffix == "json":
                            with path.open("r") as f:
                                obj = json.load(f)
                        if suffix == "toml":
                            with path.open("br") as f:
                                obj = tomllib.load(f)
                    except Exception as exc:
                        exc.add_note(f"Profile source: {path}")
                        raise exc
                    if obj:
                        if not isinstance(obj, dict):
                            raise ProfileNotObjectError(cls=cls, source=path)
                        obj["profile_name"] = name
                        profile = cls.from_object(obj, profile_source=path)
                        return profile

        if name == "default":
            resource = (
                importlib.resources.files(tinkerbox.builtin.__package__)
                / f"{name}-{cls.kind()}.toml"
            )
            if resource.is_file():
                logging.debug('Loading build-in %s profile "%s"', cls.kind(), name)
                obj = tomllib.loads(resource.read_text("utf-8"))
                obj["profile_name"] = name
                profile = cls.from_object(obj, profile_source="built-in")
                return profile

        raise ProfileNotFoundError(cls.kind(), name)


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


@dataclass
class InvalidProfileError(TinkerboxError):
    cls: type | None = None
    source: str | Path | None = None


class ProfileNotObjectError(InvalidProfileError):
    def __str__(self) -> str:
        parts = []
        if self.cls:
            parts.append(self.cls.__name__)
        else:
            parts.append("Profile")

        parts.append("should be an object")

        if self.source is not None:
            parts.append(f"[{self.source}]")

        return " ".join(parts)


@dataclass
class InvalidFieldError(InvalidProfileError):
    msg: str = field(kw_only=True)
    field: str | None = None
    value: Any = None

    def __str__(self) -> str:
        parts: list[str] = []

        # "object.field" prefix
        prefix = ".".join(
            filter(None, (self.cls.__name__ if self.cls else None, self.field))
        )
        if prefix:
            parts.append(f"{prefix}:")

        # main message
        parts.append(self.msg)

        # value
        if self.value is not None:
            parts.append(f"(got {self.value!r})")

        # source
        if self.source is not None:
            parts.append(f"[{self.source}]")

        return " ".join(parts)


@dataclass
class UnexpectedFieldsError(InvalidProfileError):
    cls: type | None = None
    fields: list[str] = field(default_factory=list)
    source: str | Path | None = None

    def __str__(self) -> str:
        parts = []

        if self.cls:
            parts.append(f"unexpected fields for {self.cls.__name__}:")
        else:
            parts.append("unexpected fields:")

        parts.append(", ".join(f"'{f}'" for f in self.fields))

        if self.source:
            parts.append(f"[{self.source}]")

        return " ".join(parts)


@dataclass
class ProfileNotFoundError(TinkerboxError):
    kind: ProfileKind
    name: str

    def __str__(self):
        return f"Unable to find {self.kind!r} profile {self.name!r}"


Obj = TypeVar("Obj")


def parse_enum(
    value: Any,
    factory: Callable[[Any], Obj],
    profile_cls: type,
    profile_field: str,
    profile_source: str | Path | None,
) -> Obj:
    if not isinstance(value, str):
        raise InvalidFieldError(
            msg="expecting a string",
            cls=profile_cls,
            field=profile_field,
            value=value,
            source=profile_source,
        )
    try:
        return factory(value)
    except (TypeError, ValueError, KeyError) as exc:
        raise InvalidFieldError(
            msg=str(exc),
            cls=profile_cls,
            field=profile_field,
            value=value,
            source=profile_source,
        )


def parse_enum_set(
    value: Any,
    factory: Callable[[Any], Obj],
    profile_cls: type,
    profile_field: str,
    profile_source: str | Path | None,
) -> set[Obj]:
    try:
        string_list = normalize_string_list(value)
    except TypeError:
        raise InvalidFieldError(
            msg="expecting a list of strings or string",
            cls=profile_cls,
            field=profile_field,
            value=value,
            source=profile_source,
        )
    return {factory(s) for s in string_list}


def parse_object_list(
    value: Any,
    factory: Callable[[Any], Obj],
    profile_cls: type,
    profile_field: str,
    profile_source: str | Path | None,
) -> list[Obj]:
    if not isinstance(value, list):
        raise InvalidFieldError(
            msg="expecting a list of dicts",
            cls=profile_cls,
            field=profile_field,
            value=value,
            source=profile_source,
        )
    try:
        return [factory(x) for x in value]
    except (TypeError, ValueError, KeyError) as exc:
        raise InvalidFieldError(
            msg=str(exc),
            cls=profile_cls,
            field=profile_field,
            value=value,
            source=profile_source,
        )


def parse_string(
    value: Any,
    profile_cls: type,
    profile_field: str,
    profile_source: str | Path | None,
) -> str:
    if not isinstance(value, str):
        raise InvalidFieldError(
            msg="expecting a string",
            cls=profile_cls,
            field=profile_field,
            value=value,
            source=profile_source,
        )
    return value


def parse_string_list(
    value: Any,
    profile_cls: type,
    profile_field: str,
    profile_source: str | Path | None,
) -> list[str]:
    try:
        return normalize_string_list(value)
    except TypeError:
        raise InvalidFieldError(
            msg="expecting either a list of strings or a string",
            cls=profile_cls,
            field=profile_field,
            value=value,
            source=profile_source,
        )


def parse_string_or_string_list(
    value: Any,
    profile_cls: type,
    profile_field: str,
    profile_source: str | Path | None,
) -> str | list[str]:
    if not isinstance(value, list) or not (
        all(isinstance(x, str) for x in value)
        or all(
            isinstance(x, list) and all(isinstance(y, str) for y in x) for x in value
        )
    ):
        raise InvalidFieldError(
            msg="expecting a string or a list of strings",
            cls=profile_cls,
            field=profile_field,
            value=value,
            source=profile_source,
        )
    return value


def parse_string_map(
    value: Any,
    profile_cls: type,
    profile_field: str,
    profile_source: str | Path | None,
) -> dict[str, str]:
    if isinstance(value, dict) and all(
        isinstance(k, str) and isinstance(v, str) for (k, v) in value.items()
    ):
        return value
    elif isinstance(value, list) and all(isinstance(x, list) for x in value):
        return {k: v for k, v in ((x.split("=", 1) + [""])[:2] for x in value)}
    else:
        raise InvalidFieldError(
            msg='expecting a dict with string keys and values or a list of strings in "KEY=VAL" format',
            cls=profile_cls,
            field=profile_field,
            value=value,
            source=profile_source,
        )


def normalize_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        value = [value]
    if not all(isinstance(v, str) for v in value):
        raise TypeError("value should be either string or list of strings")
    return list(w.strip() for w in itertools.chain(*(v.split(",") for v in value)))


def normalize_bool_value(value: str | int | bool) -> bool:
    if isinstance(value, str):
        if value.lower() in ["true", "yes", "y", "1"]:
            return True
        if value.lower() in ["false", "no", "n", "0"]:
            return False
    if isinstance(value, int):
        return bool(value)
    else:
        raise ValueError(f"can not convert value {value!r} to bool")
