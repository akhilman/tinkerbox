from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, replace, field
from typing import Any, Self

from tinkerbox.utils import substitute


@dataclass
class File(ABC):
    dst: str
    chmod: str | None = None
    chown: str | None = None

    @classmethod
    def from_object(cls, obj: Any) -> File:
        if not isinstance(obj, dict):
            raise TypeError("File object must be a dict")

        if "src" in obj:
            return CopyFile.from_object(obj)
        elif "content" in obj:
            return TextFile.from_object(obj)
        else:
            raise ValueError("File object must have either `src` or `content` field")

    @abstractmethod
    def to_object(self) -> dict[str, str]:
        raise NotImplementedError

    @abstractmethod
    def substitute(self, variables: dict[str, str]) -> Self:
        raise NotImplementedError


@dataclass
class CopyFile(File):
    src: str = field(kw_only=True)

    @classmethod
    def from_object(cls, obj: Any) -> Self:
        if not isinstance(obj, dict):
            raise TypeError("File object must be a dict")

        obj = {**obj}

        try:
            src = obj.pop("src")
        except KeyError:
            raise KeyError("Copy file object must have a `src` field")
        if not isinstance(src, str):
            raise TypeError("File object's `src` field must be a string")

        try:
            dst = obj.pop("dst")
        except KeyError:
            raise KeyError("Copy file object must have a `dst` field")
        if not isinstance(dst, str):
            raise TypeError("File object's `dst` field must be a string")

        chmod = obj.pop("chmod", None)
        if not isinstance(chmod, str | None):
            raise TypeError("File's `chmod` field should be a string or null")

        chown = obj.pop("chown", None)
        if not isinstance(chown, str | None):
            raise TypeError("File's `chown` field should be a string or null")

        if obj:
            raise ValueError(
                f"File object has unexpected keys: {', '.join(obj.keys())}"
            )

        return cls(src=src, dst=dst, chmod=chmod, chown=chown)

    @classmethod
    def from_argument(cls, arg: str) -> Self:
        parts = arg.split(":")
        match parts:
            case [src]:
                return cls(src=src, dst=src)
            case [src, dst]:
                return cls(src=src, dst=dst)
            case [src, dst, opts]:
                pass
            case _:
                raise ValueError(f"Incorrect file argument format: {arg}")

        parts = opts.split(",")
        opts_obj = {}
        for part in parts:
            match part.split("=", 1):
                case [key, value]:
                    opts_obj[key] = value
                case _:
                    raise ValueError(f"Incorrect file argument format: {arg}")

        try:
            return cls.from_object({"src": src, "dst": dst, **opts_obj})
        except ValueError as exc:
            raise ValueError(f"Incorrect file argument: {arg}") from exc

    def to_object(self) -> dict[str, str]:
        obj = {"src": self.src, "dst": self.dst}
        if self.chmod:
            obj["chmod"] = self.chmod
        if self.chown:
            obj["chown"] = self.chown
        return obj

    def substitute(self, variables: dict[str, str]) -> Self:
        return replace(
            self,
            src=substitute(self.src, variables),
            dst=substitute(self.dst, variables),
            chown=substitute(self.chown, variables) if self.chown else None,
            chmod=substitute(self.chmod, variables) if self.chmod else None,
        )


@dataclass
class TextFile(File):
    content: str = field(kw_only=True)

    @classmethod
    def from_object(cls, obj: Any) -> Self:
        if not isinstance(obj, dict):
            raise TypeError("File object must be a dict")

        obj = {**obj}

        try:
            content = obj.pop("content")
        except KeyError:
            raise KeyError("Copy file object must have a `content` field")
        if not isinstance(content, str):
            raise TypeError("File object's `content` field must be a string")

        try:
            dst = obj.pop("dst")
        except KeyError:
            raise KeyError("Copy file object must have a `dst` field")
        if not isinstance(dst, str):
            raise TypeError("File object's `dst` field must be a string")

        chmod = obj.pop("chmod", None)
        if not isinstance(chmod, str | None):
            raise TypeError("File's `chmod` field should be a string or null")

        chown = obj.pop("chown", None)
        if not isinstance(chown, str | None):
            raise TypeError("File's `chown` field should be a string or null")

        if obj:
            raise ValueError(
                f"File object has unexpected keys: {', '.join(obj.keys())}"
            )

        return cls(content=content, dst=dst, chmod=chmod, chown=chown)

    def to_object(self) -> dict[str, str]:
        obj = {"content": self.content, "dst": self.dst}
        if self.chmod:
            obj["chmod"] = self.chmod
        if self.chown:
            obj["chown"] = self.chown
        return obj

    def substitute(self, variables: dict[str, str]) -> Self:
        return replace(
            self,
            content=substitute(self.content, variables),
            dst=substitute(self.dst, variables),
            chown=substitute(self.chown, variables) if self.chown else None,
            chmod=substitute(self.chmod, variables) if self.chmod else None,
        )
