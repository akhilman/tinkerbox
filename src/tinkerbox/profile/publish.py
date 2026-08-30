from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Self

from tinkerbox.utils import split_fields


class Protocol(StrEnum):
    TCP = "tcp"
    UDP = "udp"


@dataclass(order=True)
class PortRange:
    start: int
    end: int

    @classmethod
    def from_object(cls, port_range: Any) -> Self:
        match port_range:
            case {"start": int(start), "end": int(end)}:
                return cls(start, end)
            case str():
                return cls.from_string(port_range)
            case _:
                raise ValueError(
                    'Port range should be either a string "start-end" or a dict `{"start": int, "end": int}`'
                )

    @classmethod
    def from_string(cls, port_range: str) -> Self:
        try:
            start, end = split_fields(port_range, "-", 1)
            start = int(start)
            end = int(end)
        except ValueError as exc:
            raise ValueError(f"Invalid port range format: {port_range}") from exc
        return cls(start, end)

    def __str__(self) -> str:
        return f"{self.start}-{self.end}"

    def to_object(self) -> dict[str, int]:
        return {"start": self.start, "end": self.end}


@dataclass
class Publish:
    container_port: int | PortRange
    host_port: int | PortRange | None = None
    ip: str | None = None
    protocol: Protocol | None = None

    @classmethod
    def from_object(cls, obj: Any) -> Self:
        if isinstance(obj, str):
            return cls.from_argument(obj)
        if not isinstance(obj, dict):
            raise TypeError("Publish object should be a dict")

        obj = {**obj}

        try:
            container_port = obj.pop("container_port", obj.pop("port"))
        except KeyError:
            raise KeyError(
                "Publish object should have at least `container_port` or `port` field"
            )

        try:
            container_port = normalize_port(container_port)
        except Exception as exc:
            raise ValueError(
                "Invalid `container_port` or `port` field of the publish object"
            ) from exc

        host_port = obj.pop("host_port", None)
        if host_port is not None:
            try:
                host_port = normalize_port(host_port)
            except Exception as exc:
                raise ValueError(
                    "Invalid `host_port` field of the publish object"
                ) from exc

        ip = obj.pop("ip", None)
        if ip and not isinstance(ip, str):
            raise TypeError("Publish object's `ip` field should be a string")

        protocol = obj.pop("protocol", None)
        if protocol is not None:
            if not isinstance(protocol, str):
                raise TypeError("Publish object's `protocol` field should be a string")
            try:
                protocol = Protocol(protocol.lower())
            except Exception as exc:
                raise ValueError(
                    "Invalid `protocol` field fo the publish object"
                ) from exc

        if obj:
            raise ValueError(
                f"Publish object has unexpected fields: {', '.join(obj.keys())}"
            )

        return cls(container_port, host_port, ip, protocol)

    @classmethod
    def from_argument(cls, publish: str) -> Self:
        parts = split_fields(publish, ":", 2)
        ip = None
        host_port = None
        match parts:
            case [container_port_protocol]:
                pass
            case [host_port, container_port_protocol]:
                pass
            case [host_port, ip, container_port_protocol]:
                pass
            case _:
                raise ValueError(f"Invalid publish format: {publish}")

        parts = split_fields(container_port_protocol, "/")
        protocol = None
        match parts:
            case [container_port]:
                pass
            case [container_port, protocol]:
                pass
            case _:
                raise ValueError(f"Invalid publish format: {publish}")

        try:
            container_port = normalize_port(container_port)
        except Exception as exc:
            raise ValueError(f"Invalid container port format {publish}") from exc

        if host_port is not None:
            try:
                host_port = normalize_port(host_port)
            except Exception as exc:
                raise ValueError(f"Invalid host port format {publish}") from exc

        if protocol is not None:
            try:
                protocol = Protocol(protocol.lower())
            except Exception as exc:
                raise ValueError(
                    f'Protocol must me either "tcp" or "udp", but "{protocol}" is given'
                ) from exc

        return cls(container_port, host_port, ip, protocol)

    def to_object(self) -> dict[str, int | str | dict[str, int]]:
        obj = {}
        obj["container_port"] = port_to_object(self.container_port)
        if self.host_port is not None:
            obj["host_port"] = port_to_object(self.host_port)
        if self.ip:
            obj["ip"] = self.ip
        if self.protocol:
            obj["protocol"] = str(self.protocol)
        return obj

    def to_argument(self) -> str:
        arg = f"{self.container_port}"
        if self.protocol:
            arg = f"{arg}/{self.protocol}"
        if self.host_port is not None:
            arg = f"{self.host_port}:{arg}"
        if self.ip:
            arg = f"{self.ip}:{arg}"

        return arg


def normalize_port(container_port: Any) -> int | PortRange:
    if isinstance(container_port, int):
        pass
    elif isinstance(container_port, str):
        if "-" in container_port:
            container_port = PortRange.from_string(container_port)
        else:
            container_port = int(container_port)
    elif isinstance(container_port, dict):
        container_port = PortRange.from_object(container_port)
    else:
        raise TypeError(
            "container_Port object should be either an int or a string or a dict"
        )

    return container_port


def port_to_object(port: int | PortRange) -> int | dict[str, int]:
    if isinstance(port, PortRange):
        return port.to_object()
    return port
