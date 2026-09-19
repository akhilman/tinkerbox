from dataclasses import dataclass, replace, asdict
from typing import Any, Self

from tinkerbox.utils import split_fields, substitute


@dataclass
class Exec:
    """
    Represents a `buildah run` command.
    """

    command: str | list[str]
    user: str | None = None
    work_dir: str | None = None

    @classmethod
    def from_object(cls, obj: Any) -> Self:
        if isinstance(obj, str):
            return cls.from_argument(obj)
        elif not isinstance(obj, dict):
            raise TypeError("Exec should be either a dict or a string")

        obj = {**obj}

        try:
            command = obj.pop("command")
        except KeyError:
            raise ValueError("Exec should have at least `command` field")
        if not isinstance(command, str) and not (
            isinstance(command, list) and all(isinstance(x, str) for x in command)
        ):
            raise TypeError(
                "Exec's `command` field should be a string or list of strings"
            )

        user = obj.pop("user", None)
        if not isinstance(user, str | None):
            raise TypeError("Exec's `user` field should be a string or nil")

        work_dir = obj.pop("mount", None)
        if not isinstance(user, str | None):
            raise TypeError("Exec's `work_dir` field should be a string or nil")

        if obj:
            raise ValueError(
                f"Exec object has unexpected fields: {', '.join(obj.keys())}"
            )

        return cls(
            command=command,
            user=user,
            work_dir=work_dir,
        )

    @classmethod
    def from_argument(cls, arg: str) -> Self:
        """Parse from [USER:[WORK_DIR:]]COMMAND string"""
        parts = split_fields(arg, ":")

        match parts:
            case [command]:
                return cls(command)
            case [user, command]:
                return cls(command, user)
            case [user, work_dir, command]:
                return cls(command, user, work_dir)
            case _:
                raise ValueError(f"Invalid exec format: {arg}")

    def to_object(
        self, fill_unset=False
    ) -> dict[str, str | list[dict[str, str]] | None]:
        return {k: v for k, v in asdict(self).items() if v is not None or fill_unset}

    def substitute(self, variables: dict[str, str]) -> Self:
        if isinstance(self.command, list):
            command = [substitute(x, variables) for x in self.command]
        else:
            command = substitute(self.command, variables)
        return replace(
            self,
            command=command,
            user=substitute(self.user, variables) if self.user else None,
            work_dir=substitute(self.work_dir, variables) if self.work_dir else None,
        )
