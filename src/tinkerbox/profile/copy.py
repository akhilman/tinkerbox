from pathlib import Path
from dataclasses import dataclass, replace, asdict
from typing import Any, Self

from tinkerbox.utils import split_fields, substitute


@dataclass
class Copy:
    """
    Copy a file or directory to the a container.
    """

    src: Path
    dst: Path | None = None
    src_container: str | None = None

    @classmethod
    def from_object(cls, obj: Any) -> Self:
        if isinstance(obj, str):
            return cls.from_argument(obj)
        elif not isinstance(obj, dict):
            raise TypeError("Copy should be either a dict or a string")

        obj = {**obj}

        try:
            src = obj.pop("src")
        except KeyError:
            raise ValueError("Copy should have at least a `src` field")
        if not isinstance(src, str):
            raise TypeError(
                "Copy's `src` field should be a string or a list of strings"
            )

        dst = obj.pop("dst", None)
        if dst is not None and not isinstance(dst, str):
            raise TypeError("Copy's `dst` field should be a string or nil")

        src_container = obj.pop("src_container", None)
        if src_container is not None and not isinstance(src_container, str):
            raise TypeError("Copy's `src_container` field should be a string or nil")

        return cls(src=Path(src), dst=Path(dst), src_container=src_container)

    @classmethod
    def from_argument(cls, arg: str) -> Self:
        """
        Parse from [SRC_CONTAINER:]SRC[:DST] string.
        If SRC_CONTAINER is specified, SRC is read from that container.
        DST takes precedence as the destination; without DST,
        the destination is determined automatically.
        """
        parts = split_fields(arg, ":")

        match parts:
            case [src]:
                return cls(Path(src))
            case [src, dst]:
                return cls(Path(src), dst=Path(dst))
            case [src_container, src, dst]:
                return cls(Path(src), dst=Path(dst), src_container=src_container)
            case _:
                raise ValueError(f"Invalid copy format: {arg}")

    def to_object(
        self, fill_unset=False
    ) -> dict[str, str | list[dict[str, str]] | None]:
        return {
            k: str(v) for k, v in asdict(self).items() if v is not None or fill_unset
        }

    def substitute(self, variables: dict[str, str]) -> Self:
        return type(self)(
            src=Path(substitute(str(self.src), variables)),
            dst=Path(substitute(str(self.dst), variables)) if self.dst else None,
            src_container=substitute(self.src_container, variables)
            if self.src_container
            else None,
        )
