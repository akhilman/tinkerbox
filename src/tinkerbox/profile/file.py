from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field, replace
from typing import Any, Self

from tinkerbox.utils import normalize_bool_value, split_fields, substitute


@dataclass
class File(ABC):
    # TODO: Allow more ADD arguments.
    dst: str
    chmod: str | None = None
    chown: str | None = None

    @classmethod
    def from_object(cls, obj: Any) -> File:
        if isinstance(obj, str):
            return CopyFile.from_argument(obj)
        if not isinstance(obj, dict):
            raise TypeError("File object must be a dict")

        if "src" in obj:
            return CopyFile.from_object(obj)
        elif "content" in obj:
            return TextFile.from_object(obj)
        else:
            raise ValueError("File object must have either `src` or `content` field")

    @abstractmethod
    def to_object(self) -> dict[str, str | list[str] | bool | None]:
        raise NotImplementedError

    @abstractmethod
    def substitute(self, variables: dict[str, str]) -> Self:
        raise NotImplementedError


@dataclass
class CopyFile(File):
    src: str = field(kw_only=True)
    keep_git_dir: bool | None = None
    checksum: str | None = None
    link: bool | None = None
    unpack: bool | None = None
    exclude: list[str] = field(default_factory=list)

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

        keep_git_dir = obj.pop("keep-git-dir", None)
        if keep_git_dir is not None:
            try:
                keep_git_dir = normalize_bool_value(keep_git_dir)
            except ValueError as err:
                err.add_note("Failed to convert file's `keep-git-dir` field to bool")
                raise err

        checksum = obj.pop("checksum", None)
        if not isinstance(checksum, str | None):
            raise TypeError("File's `checksum` field should be a string or null")

        link = obj.pop("link", None)
        if link is not None:
            try:
                link = normalize_bool_value(link)
            except ValueError as err:
                err.add_note("Failed to convert file's `link` field to bool")
                raise err

        unpack = obj.pop("unpack", None)
        if unpack is not None:
            try:
                unpack = normalize_bool_value(unpack)
            except ValueError as err:
                err.add_note("Failed to convert file's `unpack` field to bool")
                raise err

        exclude = obj.pop("exclude", [])
        if not isinstance(exclude, list) or not all(
            isinstance(x, str) for x in exclude
        ):
            raise TypeError("File's `exclude` field should be a list of strings")

        if obj:
            raise ValueError(
                f"File object has unexpected keys: {', '.join(obj.keys())}"
            )

        return cls(
            src=src,
            dst=dst,
            chmod=chmod,
            chown=chown,
            keep_git_dir=keep_git_dir,
            checksum=checksum,
            link=link,
            unpack=unpack,
            exclude=exclude,
        )

    @classmethod
    def from_argument(cls, arg: str) -> Self:
        parts = split_fields(arg, ":")
        # Fix urls.
        if parts[0] in ("git", "http", "https"):
            try:
                parts[0] = parts[0] + ":" + parts.pop(1)
            except IndexError:
                raise ValueError(f"Incorrect file argument format: {arg}")

        match parts:
            case [src]:
                return cls(src=src, dst=src)
            case [src, dst]:
                return cls(src=src, dst=dst)
            case [src, dst, opts]:
                pass
            case _:
                raise ValueError(f"Incorrect file argument format: {arg}")

        parts = split_fields(opts, ",")
        opts_obj = {}
        for part in parts:
            match split_fields(part, "=", 1):
                case [key] if key in ["keep-git-dir", "link", "unpack"]:
                    opts_obj[key] = True
                case ["exclude", value]:
                    if (exclude := opts_obj.get("exclude", None)) and isinstance(
                        exclude, list
                    ):
                        exclude.append(value)
                    else:
                        opts_obj["exclude"] = [value]
                case [key, value]:
                    opts_obj[key] = value
                case _:
                    raise ValueError(f"Incorrect file argument format: {arg}")

        try:
            return cls.from_object({"src": src, "dst": dst, **opts_obj})
        except ValueError as exc:
            raise ValueError(f"Incorrect file argument: {arg}") from exc

    def to_object(self) -> dict[str, str | list[str] | bool | None]:
        return asdict(self)

    def substitute(self, variables: dict[str, str]) -> Self:
        # TODO: Handle files from config directories and built-ins.
        return replace(
            self,
            src=substitute(self.src, variables),
            dst=substitute(self.dst, variables),
            chown=substitute(self.chown, variables) if self.chown else None,
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

    def to_object(self) -> dict[str, str | list[str] | bool | None]:
        return asdict(self)

    def substitute(self, variables: dict[str, str]) -> Self:
        return replace(
            self,
            content=substitute(self.content, variables),
            dst=substitute(self.dst, variables),
            chown=substitute(self.chown, variables) if self.chown else None,
            chmod=substitute(self.chmod, variables) if self.chmod else None,
        )
