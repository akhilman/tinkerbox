from collections.abc import Iterator
from enum import StrEnum
from typing import Self


class AliasEnum(StrEnum):
    @classmethod
    def _missing_(cls, value: object) -> Self | None:
        if not isinstance(value, str):
            return None

        return cls.aliases().get(value)

    @classmethod
    def aliases(cls) -> dict[str, Self]:
        return {}

    @classmethod
    def all_values(cls) -> Iterator[str]:
        for e in cls:
            yield e.value
            for k, v in sorted(cls.aliases().items()):
                if v == e:
                    yield k
