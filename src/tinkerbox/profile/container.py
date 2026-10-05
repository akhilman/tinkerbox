from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Self

from tinkerbox.alias_enum import AliasEnum
from tinkerbox.utils import normalize_string_list, random_string, substitute

from . import InvalidFieldError, Profile, ProfileKind, UnexpectedFieldsError
from .copy import Copy
from .device import Device
from .exec import Exec
from .mount import Mount
from .network import Network
from .publish import Publish
from .volume import Volume


class ContainerOverride(AliasEnum):
    ALL = "all"
    DEVICES = "devices"
    ENV = "env"
    MOUNTS = "mounts"
    NETWORKS = "networks"
    PASSTHROUGH = "passthrough"
    PUBLISH = "publish"
    VOLUMES = "volumes"
    COPY = "copy"
    EXEC = "exec"
    PASS_ENV = "pass-env"

    @classmethod
    def aliases(cls) -> dict[str, "ContainerOverride"]:
        return {
            "d": ContainerOverride.DEVICES,
            "e": ContainerOverride.ENV,
            "E": ContainerOverride.PASS_ENV,
            "m": ContainerOverride.MOUNTS,
            "n": ContainerOverride.NETWORKS,
            "p": ContainerOverride.PUBLISH,
            "s": ContainerOverride.PASSTHROUGH,
            "v": ContainerOverride.VOLUMES,
            "c": ContainerOverride.COPY,
            "x": ContainerOverride.EXEC,
        }


class Passthrough(AliasEnum):
    ALL = "all"
    DBUS = "dbus"
    GPU = "gpu"
    PIPEWIRE = "pipewire"
    PULSEAUDIO = "pulse"
    WAYLAND = "wayland"
    X11 = "x11"

    @classmethod
    def aliases(cls) -> dict[str, "Passthrough"]:
        return {
            "a": Passthrough.ALL,
            "pw": Passthrough.PIPEWIRE,
            "pa": Passthrough.PULSEAUDIO,
            "x": Passthrough.X11,
            "w": Passthrough.WAYLAND,
            "g": Passthrough.GPU,
            "b": Passthrough.DBUS,
        }


@dataclass
class ContainerProfile(Profile):
    name: str | None = None
    image: str | None = None
    environment: dict[str, str] = field(default_factory=dict)
    passthrough: set[Passthrough] = field(default_factory=set)
    devices: list[Device] = field(default_factory=list)
    mounts: list[Mount] = field(default_factory=list)
    volumes: list[Volume] = field(default_factory=list)
    networks: list[Network] = field(default_factory=list)
    publish: list[Publish] = field(default_factory=list)
    copy: list[Copy] = field(default_factory=list)
    exec: list[Exec] = field(default_factory=list)
    override: set[ContainerOverride] = field(default_factory=set)
    pass_environment: set[str] = field(default_factory=set)
    enter_command: str | None = None

    @staticmethod
    def kind() -> ProfileKind:
        return ProfileKind.CONTAINER

    @classmethod
    def from_object(
        cls, obj: dict[str, Any], profile_source: str | Path | None = None
    ) -> Self:

        obj = {**obj}
        profile = super().from_object(obj)

        if name := obj.pop("name", None):
            if not isinstance(name, str):
                raise InvalidFieldError(
                    msg="image's `name` field should be a string",
                    cls=cls,
                    field="name",
                    value=name,
                    source=profile_source,
                )
            profile.name = name

        if image := obj.pop("image", None):
            if not isinstance(image, str):
                raise InvalidFieldError(
                    msg="image's `image` field should be a string",
                    cls=cls,
                    field="image",
                    value=image,
                    source=profile_source,
                )
            profile.image = image

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
                raise InvalidFieldError(
                    msg='container\'s `environment` field should be a dict with string keys and values or list of strings in "KEY=VAL" format',
                    cls=cls,
                    field="environment",
                    value=environment,
                    source=profile_source,
                )
            profile.environment = environment

        if passthrough := obj.pop("passthrough", None):
            try:
                passthrough = normalize_string_list(passthrough)
            except TypeError:
                raise InvalidFieldError(
                    msg="container's `passthrough` field should be either list of strings or string",
                    cls=cls,
                    field="passthrough",
                    value=passthrough,
                    source=profile_source,
                )
            profile.passthrough = {Passthrough(s) for s in passthrough}

        if devices := obj.pop("devices", None):
            if not isinstance(devices, list):
                raise InvalidFieldError(
                    msg="container's `devices` field should be a list of dicts",
                    cls=cls,
                    field="devices",
                    value=devices,
                    source=profile_source,
                )
            try:
                profile.devices = [Device.from_object(x) for x in devices]
            except (TypeError, ValueError, KeyError) as exc:
                raise InvalidFieldError(
                    msg=str(exc),
                    cls=cls,
                    field="devices",
                    value=devices,
                    source=profile_source,
                )

        if mounts := obj.pop("mounts", None):
            if not isinstance(mounts, list):
                raise InvalidFieldError(
                    msg="container's `mounts` field should be a list of dicts",
                    cls=cls,
                    field="mounts",
                    value=mounts,
                    source=profile_source,
                )
            try:
                profile.mounts = [Mount.from_object(x) for x in mounts]
            except (TypeError, ValueError, KeyError) as exc:
                raise InvalidFieldError(
                    msg=str(exc),
                    cls=cls,
                    field="mounts",
                    value=mounts,
                    source=profile_source,
                )

        if volumes := obj.pop("volumes", None):
            if not isinstance(volumes, list):
                raise InvalidFieldError(
                    msg="container's `volumes` field should be a list of dicts",
                    cls=cls,
                    field="volumes",
                    value=volumes,
                    source=profile_source,
                )
            try:
                profile.volumes = [Volume.from_object(x) for x in volumes]
            except (TypeError, ValueError, KeyError) as exc:
                raise InvalidFieldError(
                    msg=str(exc),
                    cls=cls,
                    field="volumes",
                    value=volumes,
                    source=profile_source,
                )

        if networks := obj.pop("networks", None):
            if not isinstance(networks, list):
                raise InvalidFieldError(
                    msg="container's `networks` field should be a list of dicts",
                    cls=cls,
                    field="networks",
                    value=networks,
                    source=profile_source,
                )
            try:
                profile.networks = [Network.from_object(x) for x in networks]
            except (TypeError, ValueError, KeyError) as exc:
                raise InvalidFieldError(
                    msg=str(exc),
                    cls=cls,
                    field="networks ",
                    value=networks,
                    source=profile_source,
                )

        if publish := obj.pop("publish", None):
            if not isinstance(publish, list):
                raise InvalidFieldError(
                    msg="container's `publish` field should be a list of dicts",
                    cls=cls,
                    field="publish",
                    value=publish,
                    source=profile_source,
                )
            try:
                profile.publish = [Publish.from_object(x) for x in publish]
            except (TypeError, ValueError, KeyError) as exc:
                raise InvalidFieldError(
                    msg=str(exc),
                    cls=cls,
                    field="publish ",
                    value=publish,
                    source=profile_source,
                )

        if copy := obj.pop("copy", None):
            if not isinstance(copy, list):
                raise InvalidFieldError(
                    msg="container's `copy` field should be a list of dicts",
                    cls=cls,
                    field="copy",
                    value=copy,
                    source=profile_source,
                )
            try:
                profile.copy = [Copy.from_object(x) for x in copy]
            except (TypeError, ValueError, KeyError) as exc:
                raise InvalidFieldError(
                    msg=str(exc),
                    cls=cls,
                    field="copy",
                    value=copy,
                    source=profile_source,
                )

        if exec := obj.pop("exec", None):
            if not isinstance(exec, list):
                raise InvalidFieldError(
                    msg="container's `exec` field should be a list of dicts",
                    cls=cls,
                    field="exec",
                    value=exec,
                    source=profile_source,
                )
            try:
                profile.exec = [Exec.from_object(x) for x in exec]
            except (TypeError, ValueError, KeyError) as exc:
                raise InvalidFieldError(
                    msg=str(exc),
                    cls=cls,
                    field="exec",
                    value=exec,
                    source=profile_source,
                )

        if pass_environment := obj.pop("pass_environment", None):
            try:
                pass_environment = normalize_string_list(pass_environment)
            except TypeError:
                raise InvalidFieldError(
                    msg="container's `pass_environment` field should be either list of strings or string",
                    cls=cls,
                    field="pass_environment",
                    value=pass_environment,
                    source=profile_source,
                )
            profile.pass_environment = set(pass_environment)

        if enter_command := obj.pop("enter_command", None):
            if not isinstance(enter_command, str):
                raise InvalidFieldError(
                    msg="image's `enter_command` field should be a string",
                    cls=cls,
                    field="enter_command",
                    value=enter_command,
                    source=profile_source,
                )
            profile.enter_command = enter_command

        if override := obj.pop("override", None):
            try:
                override = normalize_string_list(override)
            except TypeError:
                raise InvalidFieldError(
                    msg="container's `override` field should be either list of strings or string",
                    cls=cls,
                    field="override",
                    value=override,
                    source=profile_source,
                )
            profile.override = {ContainerOverride(o) for o in override}

        if obj:
            raise UnexpectedFieldsError(
                fields=list(obj.keys()),
                cls=cls,
                source=profile_source,
            )

        return profile

    def to_object(self, fill_unset=False) -> dict[str, Any]:
        obj = super().to_object(fill_unset)
        if fill_unset or self.name:
            obj["name"] = self.name
        if fill_unset or self.image:
            obj["image"] = self.image
        if fill_unset or self.passthrough:
            obj["passthrough"] = list(sorted(map(str, self.passthrough)))
        if fill_unset or self.environment:
            obj["environment"] = self.environment
        if fill_unset or self.mounts:
            obj["mounts"] = [x.to_object() for x in self.mounts]
        if fill_unset or self.volumes:
            obj["volumes"] = [x.to_object() for x in self.volumes]
        if fill_unset or self.networks:
            obj["networks"] = [x.to_object() for x in self.networks]
        if fill_unset or self.publish:
            obj["publish"] = [x.to_object() for x in self.publish]
        if fill_unset or self.devices:
            obj["devices"] = [x.to_object() for x in self.devices]
        if fill_unset or self.copy:
            obj["copy"] = [x.to_object() for x in self.copy]
        if fill_unset or self.exec:
            obj["exec"] = [x.to_object() for x in self.exec]
        if fill_unset or self.override:
            obj["override"] = list(sorted(map(str, self.override)))
        if fill_unset or self.pass_environment:
            obj["pass_environment"] = list(sorted(self.pass_environment))
        if fill_unset or self.enter_command:
            obj["enter_command"] = self.enter_command

        return obj

    def merge(self, other: Self) -> Self:
        merged = super().merge(other)

        merged.name = self.name
        if other.name is not None:
            merged.name = other.name

        merged.image = self.image
        if other.image is not None:
            merged.image = other.image

        if not other.override & {ContainerOverride.ENV, ContainerOverride.ALL}:
            merged.environment.update(**self.environment)
        merged.environment.update(**other.environment)

        if not other.override & {ContainerOverride.PASSTHROUGH, ContainerOverride.ALL}:
            merged.passthrough |= self.passthrough
        merged.passthrough |= other.passthrough

        if not other.override & {ContainerOverride.DEVICES, ContainerOverride.ALL}:
            merged.devices.extend(self.devices)
        merged.devices.extend(other.devices)

        if not other.override & {ContainerOverride.MOUNTS, ContainerOverride.ALL}:
            merged.mounts.extend(self.mounts)
        merged.mounts.extend(other.mounts)

        if not other.override & {ContainerOverride.VOLUMES, ContainerOverride.ALL}:
            merged.volumes.extend(self.volumes)
        merged.volumes.extend(other.volumes)

        if not other.override & {ContainerOverride.NETWORKS, ContainerOverride.ALL}:
            merged.networks.extend(self.networks)
        merged.networks.extend(other.networks)

        if not other.override & {ContainerOverride.PUBLISH, ContainerOverride.ALL}:
            merged.publish.extend(self.publish)
        merged.publish.extend(other.publish)

        if not other.override & {ContainerOverride.COPY, ContainerOverride.ALL}:
            merged.copy.extend(self.copy)
        merged.copy.extend(other.copy)

        if not other.override & {ContainerOverride.EXEC, ContainerOverride.ALL}:
            merged.exec.extend(self.exec)
        merged.exec.extend(other.exec)

        if not other.override & {ContainerOverride.PASS_ENV, ContainerOverride.ALL}:
            merged.pass_environment.update(self.pass_environment)
        merged.pass_environment.update(other.pass_environment)

        merged.enter_command = self.enter_command
        if other.enter_command is not None:
            merged.enter_command = other.enter_command

        merged.override = self.override | other.override

        return merged

    def variables(self) -> dict[str, str]:
        variables = super().variables()
        # TODO: Load variables form image.
        if image := self.image:
            variables["CONTAINER_IMAGE"] = image
        variables["CONTAINER_NAME"] = (
            substitute(self.name, variables)
            if self.name
            else variables["PROFILE_NAME"] + random_string()
        )
        return variables

    def substitute(self, variables: dict[str, str] | None = None) -> Self:
        variables = {**self.variables(), **(variables or {})}
        return replace(
            self,
            name=variables.get("CONTAINER_NAME", self.name),
            image=variables.get("CONTAINER_IMAGE", self.image),
            environment={
                k: substitute(v, variables) for k, v in self.environment.items()
            },
            devices=[x.substitute(variables) for x in self.devices],
            mounts=[x.substitute(variables) for x in self.mounts],
            volumes=[x.substitute(variables) for x in self.volumes],
            copy=[x.substitute(variables) for x in self.copy],
            exec=[x.substitute(variables) for x in self.exec],
            enter_command=(
                substitute(self.enter_command, variables)
                if self.enter_command
                else None
            ),
        )
