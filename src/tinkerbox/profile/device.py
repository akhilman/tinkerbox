from tinkerbox.utils import substitute
from enum import StrEnum
from typing import Self, Any
from dataclasses import dataclass, field, replace


class DevicePermission(StrEnum):
    READ = "r"
    WRITE = "w"
    MKNOD = "m"


@dataclass
class Device:
    host_device: str
    container_device: str | None = None
    permissions: set[DevicePermission] = field(default_factory=set)

    @classmethod
    def from_object(cls, device: Any) -> Self:
        if isinstance(device, str):
            return cls.from_argument(device)
        elif not isinstance(device, dict):
            raise TypeError("Device should be either a dict or a string")

        try:
            host_device = device.pop("host_device")
        except KeyError:
            raise ValueError("Device should have at least `host_device` field")
        if not isinstance(host_device, str):
            raise TypeError("Device's `host_device` field should be a string")

        container_device = device.pop("container_device", None)
        if not isinstance(container_device, str | None):
            raise TypeError("Device's `container_device` field should be a string")

        permissions = device.pop("permissions", list)
        if isinstance(permissions, str):
            permissions = set(map(DevicePermission, permissions.replace(",", "")))
        elif isinstance(permissions, list):
            permissions = set(map(DevicePermission, permissions))
        else:
            raise TypeError(
                "Device's `permissions` field must be string or list of strings"
            )

        if device:
            raise ValueError(
                f"Device has unexpected fields: {', '.join(device.keys())}"
            )

        return cls(
            host_device=host_device,
            container_device=container_device,
            permissions=permissions,
        )

    @classmethod
    def from_argument(cls, device: str) -> Self:
        """
        Converts from Podman `--device` format: `host-device[:container-device][:permissions]`
        """
        parts = device.split(":", 2)

        match parts:
            case [host_device]:
                return cls(host_device=host_device)
            case [host_device, container_device]:
                return cls(host_device=host_device, container_device=container_device)
            case [host_device, container_device, permissions]:
                permissions = set(map(DevicePermission, permissions.replace(",", "")))
                return cls(
                    host_device=host_device,
                    container_device=container_device,
                    permissions=permissions,
                )
            case _:
                raise ValueError(f"Invalid device format: {device}")

    def to_object(self) -> dict[str, str | list[str]]:
        obj = {"host_device": self.host_device}
        if self.container_device:
            obj["container_device"] = self.container_device
        if self.permissions:
            obj["permissions"] = list(map(str, self.permissions))

        return obj

    def to_argument(self) -> str:
        """
        Converts to Podman `--device` format: `host-device[:container-device][:permissions]`
        """
        arg = f"{self.host_device}"
        if self.container_device:
            arg = f"{arg}:{self.container_device}"
        elif self.permissions:
            arg = f"{arg}:{self.host_device}"
        if self.permissions:
            perms = "".join(map(str, self.permissions))
            arg = f"{arg}:{perms}"

        return arg

    def substitute(self, variables: dict[str, str]) -> Self:
        return replace(
            self,
            host_device=substitute(self.host_device, variables),
            container_device=(
                substitute(self.container_device, variables)
                if self.container_device
                else None
            ),
        )
