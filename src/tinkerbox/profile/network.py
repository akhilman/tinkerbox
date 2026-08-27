from dataclasses import dataclass, field
from typing import Any, Self


@dataclass
class Network:
    """
    Represents a --network  with separate, typed fields.
    """

    mode: str
    options: dict[str, str | None] = field(default_factory=dict)

    @classmethod
    def from_object(cls, obj: Any) -> Self:
        if isinstance(obj, str):
            return cls.from_argument(obj)
        elif not isinstance(obj, dict):
            raise TypeError("Network should be either a dict or a string")

        obj = {**obj}

        try:
            mode = obj.pop("mode")
        except KeyError:
            raise ValueError("Network should have at least `mode` field")
        if not isinstance(mode, str):
            raise TypeError("Network's `mode` field should be a string")

        options = {k: (v if v else None) for k, v in obj.items()}
        if not all(
            isinstance(k, str) and isinstance(v, str | None) for k, v in options.items()
        ):
            raise TypeError("Network options should be strings or nils")

        return cls(mode, options=options)

    @classmethod
    def from_argument(cls, volume: str) -> Self:
        """Parse from Podman --network format: MODE:MODE-SPECIFIC-OPTION[,...] string"""
        parts = volume.split(":", 1)

        match parts:
            case [mode, options]:
                pass
            case [mode]:
                options = ""
                pass

        obj = {"mode": mode}

        for opt in options.split(","):
            key_val = opt.split("=", 1)
            match key_val:
                case [key, val]:
                    obj[key] = val
                case [key]:
                    obj[key] = None

        return cls.from_object(obj)

    def to_object(self) -> dict[str, str | None]:
        return {"mode": self.mode, **self.options}

    def to_argument(self) -> str:
        """Convert to Podman --network format: MODE:MODE-SPECIFIC-OPTION[,...]"""

        arg = f"{self.mode}"
        if self.options:
            arg += ":"
        for key, val in self.options.items():
            if val:
                arg += f",{key}={val}"
            else:
                arg += f",{key}"

        return arg
