from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any, Self

from tinkerbox.utils import normalize_bool_value, split_fields, substitute


@dataclass
class Add(ABC):
    # TODO: Allow more ADD arguments.
    dst: Path = field(kw_only=True)
    chmod: str | None = None
    chown: str | None = None

    @classmethod
    def from_object(cls, obj: Any) -> Add:
        if isinstance(obj, str):
            return AddFile.from_argument(obj)
        if not isinstance(obj, dict):
            raise TypeError("File object must be a dict")

        if "src" in obj:
            return AddFile.from_object(obj)
        elif "url" in obj:
            return AddUrl.from_object(obj)
        elif "content" in obj:
            return AddText.from_object(obj)
        else:
            raise ValueError(
                "File object must have either `src`, `url` or `content` field"
            )

    @abstractmethod
    def to_object(self, fill_unset=False) -> dict[str, str | list[str] | bool | None]:
        _ = fill_unset
        raise NotImplementedError

    @abstractmethod
    def substitute(self, variables: dict[str, str]) -> Self:
        _ = variables
        raise NotImplementedError


@dataclass
class AddFile(Add):
    src: Path = field(kw_only=True)
    keep_git_dir: bool | None = None
    checksum: str | None = None
    link: bool | None = None
    unpack: bool | None = None
    exclude: list[str] = field(default_factory=list)

    @classmethod
    def from_object(cls, obj: Any) -> Self:
        if not isinstance(obj, dict):
            raise TypeError("Add value must be a dict")

        rest = {**obj}

        try:
            src = rest.pop("src")
        except KeyError:
            raise KeyError("Copy file object must have a `src` field")
        if not isinstance(src, str):
            raise TypeError("File object's `src` field must be a string")
        src = Path(src)

        try:
            dst = rest.pop("dst")
        except KeyError:
            raise KeyError("Copy file object must have a `dst` field")
        if not isinstance(dst, str):
            raise TypeError("File object's `dst` field must be a string")
        dst = Path(dst)

        base_kwargs, rest = base_obj_to_kwargs(rest)
        file_and_url_kwargs, rest = file_and_url_obj_to_kwargs(rest)

        if rest:
            raise ValueError(
                f"File object has unexpected keys: {', '.join(rest.keys())}"
            )

        return replace(
            cls(src=src, dst=dst),
            **base_kwargs,
            **file_and_url_kwargs,
        )

    @classmethod
    def from_argument(cls, arg: str) -> Self:
        parts = split_fields(arg, ":")
        match parts:
            case [src]:
                return cls(src=Path(src), dst=Path(src))
            case [src, dst]:
                return cls(src=Path(src), dst=Path(dst))
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

    def to_object(self, fill_unset=False) -> dict[str, str | list[str] | bool | None]:
        return {
            k: str(v) if isinstance(v, Path) else v
            for k, v in asdict(self).items()
            if v is not None and v != [] or fill_unset
        }

    def substitute(self, variables: dict[str, str]) -> Self:
        return replace(
            self,
            src=Path(substitute(str(self.src), variables)),
            dst=Path(substitute(str(self.dst), variables)),
            chown=substitute(self.chown, variables) if self.chown else None,
        )


@dataclass
class AddUrl(Add):
    url: str = field(kw_only=True)
    keep_git_dir: bool | None = None
    checksum: str | None = None
    link: bool | None = None
    unpack: bool | None = None
    exclude: list[str] = field(default_factory=list)

    @classmethod
    def from_object(cls, obj: Any) -> Self:
        if not isinstance(obj, dict):
            raise TypeError("Add value must be a dict")

        rest = {**obj}

        try:
            url = rest.pop("url")
        except KeyError:
            raise KeyError("Copy file object must have a `url` field")
        if not isinstance(url, str):
            raise TypeError("File object's `url` field must be a string")

        try:
            dst = rest.pop("dst")
        except KeyError:
            raise KeyError("Copy file object must have a `dst` field")
        if not isinstance(dst, str):
            raise TypeError("File object's `dst` field must be a string")
        dst = Path(dst)

        base_kwargs, rest = base_obj_to_kwargs(rest)
        file_and_url_kwargs, rest = file_and_url_obj_to_kwargs(rest)
        url_kwargs, rest = url_obj_to_kwargs(rest)

        if rest:
            raise ValueError(
                f"File object has unexpected keys: {', '.join(rest.keys())}"
            )

        return replace(
            cls(url=url, dst=dst),
            **base_kwargs,
            **file_and_url_kwargs,
            **url_kwargs,
        )

    def to_object(self, fill_unset=False) -> dict[str, str | list[str] | bool | None]:
        return {
            k: str(v) if isinstance(v, Path) else v
            for k, v in asdict(self).items()
            if v is not None and v != [] or fill_unset
        }

    def substitute(self, variables: dict[str, str]) -> Self:
        return replace(
            self,
            url=substitute(self.url, variables),
            dst=Path(substitute(str(self.dst), variables)),
            chown=substitute(self.chown, variables) if self.chown else None,
        )


@dataclass
class AddText(Add):
    content: str = field(kw_only=True)

    @classmethod
    def from_object(cls, obj: Any) -> Self:
        if not isinstance(obj, dict):
            raise TypeError("File object must be a dict")

        rest = {**obj}

        try:
            content = rest.pop("content")
        except KeyError:
            raise KeyError("Copy file object must have a `content` field")
        if not isinstance(content, str):
            raise TypeError("File object's `content` field must be a string")

        try:
            dst = rest.pop("dst")
        except KeyError:
            raise KeyError("Copy file object must have a `dst` field")
        if not isinstance(dst, str):
            raise TypeError("File object's `dst` field must be a string")

        base_kwargs, rest = base_obj_to_kwargs(rest)

        if rest:
            raise ValueError(
                f"File object has unexpected keys: {', '.join(rest.keys())}"
            )

        return replace(
            cls(content=content, dst=dst),
            **base_kwargs,
        )

    def to_object(self, fill_unset=False) -> dict[str, str | list[str] | bool | None]:
        return {
            k: str(v) if isinstance(v, Path) else v
            for k, v in asdict(self).items()
            if v is not None or fill_unset
        }

    def substitute(self, variables: dict[str, str]) -> Self:
        return replace(
            self,
            content=substitute(self.content, variables),
            dst=Path(substitute(str(self.dst), variables)),
            chown=substitute(self.chown, variables) if self.chown else None,
        )


def base_obj_to_kwargs(obj: Any) -> tuple[dict[str, str | None], dict[str, Any]]:
    if not isinstance(obj, dict):
        raise TypeError("Add value must be a dict")

    rest = {**obj}

    chmod = rest.pop("chmod", None)
    if not isinstance(chmod, str | None):
        raise TypeError("File's `chmod` field should be a string or null")

    chown = rest.pop("chown", None)
    if not isinstance(chown, str | None):
        raise TypeError("File's `chown` field should be a string or null")

    validated = {
        "chmod": chmod,
        "chown": chown,
    }
    return (validated, rest)


def file_and_url_obj_to_kwargs(
    obj: Any,
) -> tuple[dict[str, str | list[str] | bool | None], dict[str, Any]]:
    if not isinstance(obj, dict):
        raise TypeError("Add value must be a dict")

    rest = {**obj}

    link = rest.pop("link", None)
    if link is not None:
        try:
            link = normalize_bool_value(link)
        except ValueError as err:
            err.add_note("Failed to convert file's `link` field to bool")
            raise err

    unpack = rest.pop("unpack", None)
    if unpack is not None:
        try:
            unpack = normalize_bool_value(unpack)
        except ValueError as err:
            err.add_note("Failed to convert file's `unpack` field to bool")
            raise err

    exclude = rest.pop("exclude", [])
    if not isinstance(exclude, list) or not all(isinstance(x, str) for x in exclude):
        raise TypeError("File's `exclude` field should be a list of strings")

    validated = {
        "link": link,
        "unpack": unpack,
        "exclude": exclude,
    }
    return (validated, rest)


def url_obj_to_kwargs(obj: Any) -> tuple[dict[str, str | bool | None], dict[str, Any]]:
    if not isinstance(obj, dict):
        raise TypeError("Add value must be a dict")

    rest = {**obj}

    keep_git_dir = rest.pop("keep-git-dir", None)
    if keep_git_dir is not None:
        try:
            keep_git_dir = normalize_bool_value(keep_git_dir)
        except ValueError as err:
            err.add_note("Failed to convert file's `keep-git-dir` field to bool")
            raise err

    checksum = rest.pop("checksum", None)
    if not isinstance(checksum, str | None):
        raise TypeError("File's `checksum` field should be a string or null")

    validated = {
        "keep_git_dir": keep_git_dir,
        "checksum": checksum,
    }
    return (validated, rest)
