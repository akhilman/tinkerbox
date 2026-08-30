from dataclasses import dataclass, field, replace
from typing import Any, Self

from tinkerbox.alias_enum import AliasEnum
from tinkerbox.utils import normalize_string_list, random_string, substitute

from . import Profile, ProfileKind
from .device import Device
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

    @classmethod
    def aliases(cls) -> dict[str, "ContainerOverride"]:
        return {
            "d": ContainerOverride.DEVICES,
            "e": ContainerOverride.ENV,
            "m": ContainerOverride.MOUNTS,
            "n": ContainerOverride.NETWORKS,
            "p": ContainerOverride.PUBLISH,
            "s": ContainerOverride.PASSTHROUGH,
            "v": ContainerOverride.VOLUMES,
        }


class Passthrough(AliasEnum):
    DBUS = "dbus"
    GPU = "gpu"
    PIPEWIRE = "pipewire"
    PULSEAUDIO = "pulse"
    WAYLAND = "wayland"
    X11 = "x11"

    @classmethod
    def aliases(cls) -> dict[str, "Passthrough"]:
        return {
            "pw": Passthrough.PIPEWIRE,
            "pa": Passthrough.PULSEAUDIO,
            "x": Passthrough.X11,
            "w": Passthrough.WAYLAND,
            "g": Passthrough.GPU,
            "d": Passthrough.DBUS,
        }


@dataclass
class ContainerProfile(Profile):
    name: str | None = None
    environment: dict[str, str] = field(default_factory=dict)
    passthrough: set[Passthrough] = field(default_factory=set)
    devices: list[Device] = field(default_factory=list)
    mounts: list[Mount] = field(default_factory=list)
    volumes: list[Volume] = field(default_factory=list)
    networks: list[Network] = field(default_factory=list)
    publish: list[Publish] = field(default_factory=list)
    override: set[ContainerOverride] = field(default_factory=set)

    @staticmethod
    def kind() -> ProfileKind:
        return ProfileKind.CONTAINER

    @classmethod
    def from_object(cls, obj: Any) -> Self:
        if not isinstance(obj, dict):
            raise TypeError("Container profile must be a dict")

        obj = {**obj}
        profile = super().from_object(obj)

        if name := obj.pop("name", None):
            if not isinstance(name, str):
                raise TypeError("Image's `name` field should be a string")
            profile.name = name

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
                    'Container\'s `environment` field should be a dict with string keys and values or list of strings in "KEY=VAL" format'
                )
            profile.environment = environment

        if passthrough := obj.pop("passthrough", None):
            try:
                passthrough = normalize_string_list(passthrough)
            except TypeError:
                raise TypeError(
                    "Container's `passthrough` field should be either list of strings or string"
                )
            profile.passthrough = {Passthrough(s) for s in passthrough}

        if devices := obj.pop("devices", None):
            if not isinstance(devices, list):
                raise TypeError("Container's `devices` field should be a list of dicts")
            profile.devices = [Device.from_object(x) for x in devices]

        if mounts := obj.pop("mounts", None):
            if not isinstance(mounts, list):
                raise TypeError("Container's `mounts` field should be a list of dicts")
            profile.mounts = [Mount.from_object(x) for x in mounts]

        if volumes := obj.pop("volumes", None):
            if not isinstance(volumes, list):
                raise TypeError("Container's `volumes` field should be a list of dicts")
            profile.volumes = [Volume.from_object(x) for x in volumes]

        if networks := obj.pop("networks", None):
            if not isinstance(networks, list):
                raise TypeError(
                    "Container's `networks` field should be a list of dicts"
                )
            profile.networks = [Network.from_object(x) for x in networks]

        if publish := obj.pop("publish", None):
            if not isinstance(publish, list):
                raise TypeError("Container's `publish` field should be a list of dicts")
            profile.publish = [Publish.from_object(x) for x in publish]

        if override := obj.pop("override", None):
            try:
                override = normalize_string_list(override)
            except TypeError:
                raise TypeError(
                    "Container's `override` field should be either list of strings or string"
                )
            profile.override = {ContainerOverride(o) for o in override}

        if obj:
            raise ValueError(
                f"Container has unexpected fields: {', '.join(obj.keys())}"
            )

        return profile

    def to_object(self, fill_unset=False) -> dict[str, Any]:
        obj = super().to_object(fill_unset)
        if fill_unset or self.name:
            obj["name"] = self.name
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
        if fill_unset or self.override:
            obj["override"] = list(sorted(map(str, self.override)))

        return obj

    def merge(self, other: Self) -> Self:
        merged = super().merge(other)

        merged.name = self.name
        if other.name is not None:
            merged.name = other.name

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

        merged.override = self.override | other.override

        return merged

    def variables(self) -> dict[str, str]:
        variables = super().variables()
        # TODO: Load variables form image.
        variables["CONTAINER_NAME"] = (
            substitute(self.name, variables)
            if self.name
            else variables["PROFILE_NAME"] + random_string()
        )
        return variables

    def substitute(self, variables: dict[str, str] | None = None) -> Self:
        variables = {**self.variables(), **(variables or {})}
        environment = {k: substitute(v, variables) for k, v in self.environment}
        devices = [x.substitute(variables) for x in self.devices]
        mounts = [x.substitute(variables) for x in self.mounts]
        volumes = [x.substitute(variables) for x in self.volumes]
        # TODO: Substitute passthrough.
        return replace(
            super().substitute(variables=variables),
            environment=environment,
            devices=devices,
            mounts=mounts,
            volumes=volumes,
        )
