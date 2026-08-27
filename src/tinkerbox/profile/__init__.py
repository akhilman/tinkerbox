import pwd
import os
import logging
import importlib.resources
import json
import tomllib
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Self, cast

from tinkerbox.resources import config_paths
from tinkerbox.utils import normalize_string_list, substitute

from .container import ContainerOptions
from .image import ImageOptions


@dataclass
class Profile:
    # Profile options
    name: str | None = None
    source: str | Path | None = None
    description: str | None = None
    extends: list[str] = field(default_factory=list)

    user: str | None = None
    home: str | None = None

    image: ImageOptions = field(default_factory=ImageOptions)
    container: ContainerOptions = field(default_factory=ContainerOptions)

    @classmethod
    def from_object(cls, obj):
        if not isinstance(obj, dict):
            raise TypeError("Profile value should be a dict")

        obj = {**obj}
        profile = cls()

        if name := obj.pop("name", None):
            if not isinstance(name, str):
                raise TypeError("Profile name should be a string")
            profile.name = name

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

        if source := obj.pop("source", None):
            if not isinstance(source, str | Path):
                raise TypeError("Profile's `source` field should be a string")
            profile.source = source

        if user := obj.pop("user", None):
            if not isinstance(user, str):
                raise TypeError("Image's `user` field should be a string")
            profile.user = user

        if home := obj.pop("home", None):
            if not isinstance(home, str):
                raise TypeError("Image's `home` field should be a string")
            profile.home = home

        if image := obj.pop("image", None):
            profile.image = ImageOptions.from_object(image)
        if container := obj.pop("container", None):
            profile.container = ContainerOptions.from_object(container)

        if obj:
            raise ValueError(f"Profile has unexpected fields: {', '.join(obj.keys())}")

        return profile

    def to_object(self, fill_unset=False) -> dict[str, Any]:
        obj = {}
        if fill_unset or self.name:
            obj["name"] = self.name
        if fill_unset or self.description:
            obj["description"] = self.description
        if fill_unset or self.extends:
            obj["extends"] = self.extends
        if fill_unset or self.source:
            obj["source"] = str(self.source)

        if fill_unset or self.user:
            obj["user"] = self.user
        if fill_unset or self.home:
            obj["home"] = self.home

        image = self.image.to_object(fill_unset)
        if fill_unset or image:
            obj["image"] = image
        container = self.container.to_object(fill_unset)
        if fill_unset or container:
            obj["container"] = container

        return obj

    def flatten(self) -> Self:
        """
        Merges this profile over loaded profiles form the `extends` field.
        """

        visited = set()
        stack = [*self.extends]
        flat = Profile().merge(self)  # Make deep copy

        while stack:
            name = stack.pop(-1)
            if name in visited:
                continue
            visited.add(name)
            base = load_profile(name)
            stack.extend(base.extends)
            base.extends = []
            flat = base.merge(flat)

        return cast(Self, flat)

    def merge(self, other: Self) -> Self:
        merged = type(self)()

        merged.name = self.name
        if other.name is not None:
            merged.name = other.name

        merged.description = self.description
        if other.description is not None:
            merged.description = other.description

        merged.source = other.source

        merged.user = self.user
        if other.user is not None:
            merged.user = other.user

        merged.home = self.home
        if other.home is not None:
            merged.home = other.home

        merged.image = self.image.merge(other.image)
        merged.container = self.container.merge(other.container)

        return merged

    def _variables(self) -> dict[str, str]:
        variables = {k: v for k, v in os.environ.items()}

        uid = os.getuid()
        gid = os.getgid()
        user = self.user or pwd.getpwuid(uid).pw_name
        variables["UID"] = str(uid)
        variables["GID"] = str(gid)

        variables["USER"] = user

        home = substitute(self.home or pwd.getpwuid(uid).pw_dir, variables)
        variables["HOME"] = home

        description = (
            substitute(self.description, variables) if self.description else ""
        )
        variables["DESCRIPTION"] = description

        return variables

    def substitute_shallow(self) -> Self:
        """
        Substitutes `@{VAR}` only in top level fields, skipping `image` and `container`.
        """
        variables = self._variables()

        return replace(
            self,
            user=variables["USER"],
            home=variables["HOME"],
            description=variables["DESCRIPTION"],
        )

    def substitute(self) -> Self:
        """
        Substitutes `@{VAR}` in fields.
        """

        variables = self._variables()

        profile = self.substitute_shallow()
        profile.image = profile.image.substitute(variables)
        profile.container = profile.container.substitute(variables)

        return profile


def list_profiles() -> set[str]:
    profiles = {"default"}
    for dir in config_paths():
        dir = dir / "profiles"
        for path in dir.iterdir():
            if not path.is_file() or path.suffix not in [".json", ".toml"]:
                continue
            name = path.with_suffix("").name
            profiles.add(name)

    return profiles


def load_profile(name: str) -> Profile:
    for dir in config_paths():
        for suffix in ["json", "toml"]:
            path = dir / "profiles" / f"{name}.{suffix}"
            if path.is_file():
                logging.debug('Loading profile form "%s"', path)
                profile = None
                try:
                    if suffix == "json":
                        with path.open("r") as f:
                            profile = Profile.from_object(json.load(f))
                    if suffix == "toml":
                        with path.open("br") as f:
                            profile = Profile.from_object(tomllib.load(f))
                except Exception as exc:
                    exc.add_note(f"Profile source: {path}")
                    raise exc
                if profile:
                    profile.name = name
                    profile.source = path
                    return profile

    resource_path = importlib.resources.files(__package__) / f"{name}.toml"
    if resource_path.is_file():
        with importlib.resources.as_file(resource_path) as f:
            logging.debug('Loading build-in profile "%s"', name)
            text = f.read_text()
            profile = Profile.from_object(tomllib.loads(text))
            profile.name = name
            profile.source = "built-in"
            return profile

    raise FileNotFoundError(f"Profile {name} not found")
