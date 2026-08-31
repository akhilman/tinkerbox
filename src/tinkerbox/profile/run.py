from dataclasses import dataclass, replace, asdict
from typing import Any, Self

from tinkerbox.utils import split_fields, substitute


@dataclass
class Run:
    """
    Represents a `buildah run` command.
    """

    command: str | list[str]
    user: str
    mount: list[dict[str, str]] | None = None
    network: str | None = None
    security: str | None = None

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
        if not isinstance(command, str) and not (
            isinstance(command, list) and all(isinstance(x, str) for x in command)
        ):
            raise TypeError(
                "Run's `command` field should be a string or a list of strings"
            )

        user = obj.pop("user", "root")
        if not isinstance(user, str):
            raise TypeError("Run's `user` field should be a string")

        mount = obj.pop("mount", None)

        if isinstance(mount, dict):
            mount = [mount]
        if not (
            mount is None
            or isinstance(mount, list)
            and all(
                isinstance(x, dict)
                and all(isinstance(k, str) and isinstance(v, str) for k, v in x)
                for x in mount
            )
        ):
            raise TypeError("Run's `mount` field should be a dict or list of dicts")

        network = obj.pop("network", None)
        if not isinstance(network, str | None):
            raise TypeError("Run's `network` field should be a string")

        security = obj.pop("security", None)
        if not isinstance(security, str | None):
            raise TypeError("Run's `security` field should be a string")

        if obj:
            raise ValueError(
                f"Run object has unexpected fields: {', '.join(obj.keys())}"
            )

        return cls(command, user)

    @classmethod
    def from_argument(cls, arg: str) -> Self:
        """Parse from [USER:]COMMAND[:option=value[:option=...]] string"""
        parts = split_fields(arg, ":")

        match parts:
            case [command]:
                return cls(command, "root")
            case [user, command]:
                return cls(command, user)
            case [user, command, *opts]:
                kwargs = {}
                for opt in opts:
                    match split_fields(opt, "=", 1):
                        case ["mount", args]:
                            mount_args = {}
                            for arg in split_fields(args, ","):
                                try:
                                    (k, v) = split_fields(arg, "=", 1)
                                except Exception as exc:
                                    raise ValueError(
                                        f"Incorrect run option: {opt}"
                                    ) from exc
                                mount_args[k] = v
                            kwargs["mount"] = [*kwargs.get("mount", []), mount_args]
                        case ["network", value]:
                            kwargs["network"] = value
                        case ["security", value]:
                            kwargs["security"] = value
                        case _:
                            raise ValueError(f"Incorrect run option: {opt}")
                return cls(command=command, user=user, **kwargs)

            case _:
                raise ValueError(f"Invalid run format: {arg}")

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
            user=substitute(self.user, variables),
            mount=[
                {k: substitute(v, variables) for k, v in x.items()} for x in self.mount
            ]
            if self.mount
            else None,
        )
