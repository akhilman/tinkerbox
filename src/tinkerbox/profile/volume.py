from tinkerbox.utils import substitute
from typing import Any, Self
from dataclasses import dataclass, field, replace


@dataclass
class Volume:
    """
    Represents a --volume mount with separate, typed fields.
    """

    target: str  # Container path
    source: str | None = None  # Host path or volume name
    options: set[str] = field(default_factory=set)

    @classmethod
    def from_object(cls, obj: Any) -> Self:
        if isinstance(obj, str):
            return cls.from_argument(obj)
        elif not isinstance(obj, dict):
            raise TypeError("Volume should be either a dict or a string")

        obj = {**obj}

        try:
            target = obj.pop("target")
        except KeyError:
            raise ValueError("Volume should have at least `target` field")
        if not isinstance(target, str):
            raise TypeError("Volume's `target` field should be a string")

        source = obj.pop("source", None)
        if not isinstance(source, str | None):
            raise TypeError("Volume's `source` field should be a string")

        options = obj.pop("options", list)
        if isinstance(options, str):
            options = set(options.split(","))
        elif not isinstance(options, list):
            raise TypeError(
                "Volume's `options` field must be string or list of strings"
            )

        if obj:
            raise ValueError(
                f"Volume object has unexpected fields: {', '.join(obj.keys())}"
            )

        return cls(target=target, source=source, options=options)

    @classmethod
    def from_argument(cls, volume: str) -> Self:
        """Parse from Podman --volume format: [SOURCE:]TARGET[:OPTIONS]"""
        parts = volume.split(":", 2)

        match parts:
            case [target]:
                return cls(target=target)
            case [source, target]:
                return cls(target=target, source=source)
            case [source, target, options]:
                options = set(options.split(","))
                return cls(target=target, source=source, options=options)
            case _:
                raise ValueError(f"Invalid volume format: {volume}")

    def to_object(self) -> dict[str, str | list[str]]:
        obj = {"target": self.target}
        if self.source:
            obj["source"] = self.source
        if self.options:
            obj["options"] = list(self.options)

        return obj

    def to_argument(self) -> str:
        """Convert to Podman --volume format: [SOURCE:]TARGET:[OPTIONS]"""

        arg = f"{self.target}"
        if self.source:
            arg = f"{self.source}:{arg}"
        if self.options:
            opts_str = ",".join(self.options)
            arg = f"{arg}:{opts_str}"

        return arg

    def substitute(self, variables: dict[str, str]) -> Self:
        return replace(
            self,
            target=substitute(self.target, variables),
            source=substitute(self.source, variables) if self.source else None,
        )
