import secrets
import string
import itertools
import re
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


def substitute(text: str, variables: dict[str, str]) -> str:
    _VAR = re.compile(r"@\{([A-Za-z_][A-Za-z0-9_]*)\}")

    def replace(match):
        name = match.group(1)
        try:
            return variables[name]
        except KeyError:
            raise ValueError(f"variable ${name} is not defined")

    return _VAR.sub(replace, text)
