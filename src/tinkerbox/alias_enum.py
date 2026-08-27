from enum import StrEnum
from typing import Iterator, TypeVar, Type

T = TypeVar("T", bound="AliasEnum")


class AliasEnum(StrEnum):
    @classmethod
    def _missing_(cls: Type[T], value: object) -> T | None:
        if not isinstance(value, str):
            return None

        return cls.aliases().get(value)

    @classmethod
    def aliases(cls: Type[T]) -> dict[str, T]:
        return {}

    @classmethod
    def all_values(cls) -> Iterator[str]:
        for e in cls:
            yield e.value
            for k, v in sorted(cls.aliases().items()):
                if v == e:
                    yield k
