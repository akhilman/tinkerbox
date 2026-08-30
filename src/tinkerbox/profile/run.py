from dataclasses import dataclass, replace
from typing import Any, Self

from tinkerbox.utils import split_fields, substitute


@dataclass
class Run:
    """
    Represents a `buildah run` command.
    """

    # TODO: Add more RUN arguments.
    # TODO: Support run as list of strings.

    command: str
    user: str

    @classmethod
    def from_object(cls, obj: Any) -> Self:
        if isinstance(obj, str):
            return cls.from_argument(obj)
        elif not isinstance(obj, dict):
            raise TypeError("Run should be either a dict or a string")

        obj = {**obj}

        try:
            command = obj.pop("command")
        except KeyError:
            raise ValueError("Run should have at least `command` field")
        if not isinstance(command, str):
            raise TypeError("Run's `command` field should be a string")

        user = obj.pop("user", "root")
        if not isinstance(user, str):
            raise TypeError("Run's `user` field should be a string")

        if obj:
            raise ValueError(
                f"Run object has unexpected fields: {', '.join(obj.keys())}"
            )

        return cls(command, user)

    @classmethod
    def from_argument(cls, arg: str) -> Self:
        """Parse from [USER:]COMMAND string"""
        parts = split_fields(arg, ":", 1)

        match parts:
            case [command]:
                return cls(command, "root")
            case [user, command]:
                return cls(command, user)
            case _:
                raise ValueError(f"Invalid volume format: {arg}")

    def to_object(self) -> dict[str, str]:
        obj = {"command": self.command, "user": self.user}
        return obj

    def to_argument(self) -> str:
        """Convert to format: USER:COMMAND"""
        return f"{self.user}:{self.command}"

    def substitute(self, variables: dict[str, str]) -> Self:
        return replace(
            self,
            command=substitute(self.command, variables),
            user=substitute(self.user, variables),
        )
