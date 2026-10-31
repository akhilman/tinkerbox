from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Self

from tinkerbox.utils import split_fields, substitute


@dataclass
class Copy:
    """
    Copy a file or directory to the a container.
    """

    source: Path
    destination: Path | None = None
    source_container: str | None = None
    ignore_failure: bool = False

    @classmethod
    def from_object(cls, obj: Any) -> Self:
        if isinstance(obj, str):
            return cls.from_argument(obj)
        elif not isinstance(obj, dict):
            raise TypeError("copy should be either a dict or a string")

        obj = {**obj}

        source = obj.pop("source", None) or obj.pop("src", None)
        if not source:
            raise ValueError("copy should have at least a `source` field")
        if not isinstance(source, str):
            raise TypeError(
                "copy's `source` field should be a string or a list of strings"
            )

        destination = obj.pop("destination", None) or obj.pop("dst", None)
        if destination is not None and not isinstance(destination, str):
            raise TypeError("copy's `destination` field should be a string or nil")

        source_container = obj.pop("source_container", None) or obj.pop(
            "container", None
        )
        if source_container is not None and not isinstance(source_container, str):
            raise TypeError("copy's `source_container` field should be a string or nil")

        ignore_failure = obj.pop("ignore_failure", None)
        if not isinstance(ignore_failure, bool | None):
            raise TypeError("copy's `ignore_failure` field should be a bool or nil")
        ignore_failure = bool(ignore_failure)

        if obj:
            raise ValueError(
                f"copy object has unexpected fields: {', '.join(obj.keys())}"
            )

        return cls(
            source=Path(source),
            destination=Path(destination),
            source_container=source_container,
            ignore_failure=ignore_failure,
        )

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
            case [source]:
                return cls(Path(source))
            case [source, destination]:
                return cls(Path(source), destination=Path(destination))
            case [source_container, source, destination]:
                return cls(
                    Path(source),
                    destination=Path(destination),
                    source_container=source_container,
                )
            case _:
                raise ValueError(f"invalid copy format: {arg}")

    def to_object(
        self, fill_unset=False
    ) -> dict[str, str | list[dict[str, str]] | None]:
        return {
            k: str(v) if isinstance(v, Path) else v
            for k, v in asdict(self).items()
            if v is not None or fill_unset
        }

    def substitute(self, variables: dict[str, str]) -> Self:
        return replace(
            self,
            source=Path(substitute(str(self.source), variables)),
            destination=Path(substitute(str(self.destination), variables))
            if self.destination
            else None,
            source_container=substitute(self.source_container, variables)
            if self.source_container
            else None,
        )
