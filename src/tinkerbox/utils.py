import itertools
import re
import secrets
import string
from typing import Any


def normalize_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        value = [value]
    if not all(isinstance(v, str) for v in value):
        raise TypeError("Value should be either string or list of strings")
    return list(w.strip() for w in itertools.chain(*(v.split(",") for v in value)))


def random_string(length: int = 8) -> str:
    chars = string.ascii_letters + string.digits
    return "".join(secrets.choice(chars) for _ in range(length))


def split_fields(value: str, sep=":", max_splits=-1) -> list[str]:
    parts = []
    start = 0
    depth = 0

    for i, char in enumerate(value):
        if max_splits != -1 and len(parts) >= max_splits:
            break
        if char == "@" and i + 1 < len(value) and value[i + 1] == "{":
            depth += 1
        elif char == "}" and depth:
            depth -= 1
        elif char == sep and depth == 0:
            parts.append(value[start:i])
            start = i + 1

    parts.append(value[start:])
    return parts


_SUBSTITUTE_VAR = re.compile(r"@\{([A-Za-z_][A-Za-z0-9_]*)((\?|:-)([^}]*))?\}")


def substitute(text: str, variables: dict[str, str]) -> str:
    """
    Substitute variables in `text`.

    Variables use the following syntax:

        @{VAR}           Required variable. Raises ValueError if undefined.
        @{VAR?}          Optional variable. Substitutes an empty string if undefined.
        @{VAR:-default}  Substitutes `default` if the variable is undefined or empty.

    Variable names must start with a letter or underscore and contain only
    letters, digits, and underscores.

    Args:
        text: Text containing variable references.
        variables: Mapping of variable names to their values.

    Returns:
        The text with all variable references substituted.

    Raises:
        ValueError: If a required variable is not defined.
    """

    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        operator = match.group(3)
        default = match.group(4)

        if name in variables:
            value = variables[name]
            return value

        if operator == "?":
            return ""

        if operator == ":-" and default:
            return default

        raise ValueError(f"variable {name!r} is not defined")

    return _SUBSTITUTE_VAR.sub(replace, text)
