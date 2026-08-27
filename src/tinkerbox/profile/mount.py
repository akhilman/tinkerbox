from tinkerbox.utils import substitute
from typing import Any, Self
from dataclasses import dataclass, field, replace


@dataclass
class Mount:
    """
    Represents a --mount  with separate, typed fields.
    """

    mount_type: str
    options: dict[str, str | None] = field(default_factory=dict)

    @classmethod
    def from_object(cls, obj: Any) -> Self:
        if isinstance(obj, str):
            return cls.from_argument(obj)
        elif not isinstance(obj, dict):
            raise TypeError("Mount should be either a dict or a string")

        obj = {**obj}

        try:
            mount_type = obj.pop("type")
        except KeyError:
            raise ValueError("Mount should have at least `type` field")
        if not isinstance(mount_type, str):
            raise TypeError("Mount's `type` field should be a string")

        options = {k: (v if v else None) for k, v in obj.items()}
        if not all(
            isinstance(k, str) and isinstance(v, str | None) for k, v in options.items()
        ):
            raise TypeError("Mount options should be strings or nils")

        return cls(mount_type, options=options)

    @classmethod
    def from_argument(cls, volume: str) -> Self:
        """Parse from type=TYPE,TYPE-SPECIFIC-OPTION[,...] string"""
        parts = volume.split(",")

        obj = {}

        for part in parts:
            key_val = part.split("=", 1)
            match key_val:
                case [key, val]:
                    obj[key] = val
                case [key]:
                    obj[key] = None

        return cls.from_object(obj)

    def to_object(self) -> dict[str, str | None]:
        return {"type": self.mount_type, **self.options}

    def to_argument(self) -> str:
        """Convert to Podman --volume format: type=TYPE,TYPE-SPECIFIC-OPTION[,...]"""

        arg = f"{self.mount_type}"
        for key, val in self.options.items():
            if val:
                arg += f",{key}={val}"
            else:
                arg += f",{key}"

        return arg

    def substitute(self, variables: dict[str, str]) -> Self:
        return replace(
            self,
            options={
                k: (substitute(v, variables) if v else None)
                for k, v in self.options.items()
            },
        )
