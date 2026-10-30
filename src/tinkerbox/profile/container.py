from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Self

from tinkerbox.alias_enum import AliasEnum
from tinkerbox.utils import substitute

from . import (
    Profile,
    ProfileKind,
    UnexpectedFieldsError,
    parse_enum_set,
    parse_object_list,
    parse_string,
    parse_string_list,
    parse_string_map,
)
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
            profile.name = parse_string(
                name,
                cls,
                "name",
                profile_source,
            )

        if image := obj.pop("image", None):
            profile.image = parse_string(
                image,
                cls,
                "image",
                profile_source,
            )

        if environment := obj.pop("environment", None) or obj.pop("env", None):
            profile.environment = parse_string_map(
                environment,
                cls,
                "environment",
                profile_source,
            )

        if passthrough := obj.pop("passthrough", None):
            profile.passthrough = parse_enum_set(
                passthrough,
                Passthrough,
                cls,
                "passthrough",
                profile_source,
            )

        if devices := obj.pop("devices", None):
            profile.devices = parse_object_list(
                devices,
                Device.from_object,
                cls,
                "devices",
                profile_source,
            )

        if mounts := obj.pop("mounts", None):
            profile.mounts = parse_object_list(
                mounts,
                Mount.from_object,
                cls,
                "mounts",
                profile_source,
            )

        if volumes := obj.pop("volumes", None):
            profile.volumes = parse_object_list(
                volumes,
                Volume.from_object,
                cls,
                "volumes",
                profile_source,
            )

        if networks := obj.pop("networks", None):
            profile.networks = parse_object_list(
                networks,
                Network.from_object,
                cls,
                "networks",
                profile_source,
            )

        if publish := obj.pop("publish", None):
            profile.publish = parse_object_list(
                publish,
                Publish.from_object,
                cls,
                "publish",
                profile_source,
            )

        if copy := obj.pop("copy", None):
            profile.copy = parse_object_list(
                copy,
                Copy.from_object,
                cls,
                "copy",
                profile_source,
            )

        if exec := obj.pop("exec", None):
            profile.exec = parse_object_list(
                exec,
                Exec.from_object,
                cls,
                "exec",
                profile_source,
            )

        if pass_environment := obj.pop("pass_environment", None):
            profile.pass_environment = set(
                parse_string_list(
                    pass_environment,
                    cls,
                    "pass_environment",
                    profile_source,
                )
            )

        if enter_command := obj.pop("enter_command", None):
            profile.enter_command = parse_string(
                enter_command,
                cls,
                "enter_command",
                profile_source,
            )

        if override := obj.pop("override", None):
            profile.override = parse_enum_set(
                override,
                ContainerOverride,
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
        if fill_unset or self.name:
            obj["name"] = self.name
        if fill_unset or self.image:
            obj["image"] = self.image
        if fill_unset or self.passthrough:
            obj["passthrough"] = sorted(map(str, self.passthrough))
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
            obj["override"] = sorted(map(str, self.override))
        if fill_unset or self.pass_environment:
            obj["pass_environment"] = sorted(self.pass_environment)
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
        if self.image:
            variables["CONTAINER_IMAGE"] = self.image
        if self.name:
            variables["CONTAINER_NAME"] = self.name

        return variables

    def substitute(self, variables: dict[str, str]) -> Self:
        return replace(
            self,
            name=substitute(self.name, variables) if self.name else None,
            image=substitute(self.image, variables) if self.image else None,
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
