from typing import Any
import sys
from collections.abc import Iterable, Iterator


class Table:
    def __init__(self):
        self.rows: list[list[str]] = []

    def add_row(self, items: Iterable[str]):
        self.rows.append(list(items))

    def format(self) -> Iterator[str]:
        column_widths = []
        for row in self.rows:
            for n, item in enumerate(row):
                if len(column_widths) > n:
                    column_widths[n] = max(column_widths[n], len(item))
                else:
                    column_widths.append(len(item))
        for row in self.rows:
            line_parts = []
            for item, width in zip(row, column_widths):
                line_parts.append(item.ljust(width))
            yield "  ".join(line_parts)


def format_size(size: int) -> str:
    for unit in ("B", "KiB", "MiB", "GiB", "TiB", "PiB", "EiB", "ZiB", "YiB"):
        if size < 1 << 13:
            return f"{size} {unit}"
        size >>= 10
    raise OverflowError("value is to large")


def name_or_id(list_entry: dict[str, Any], *, max_id_length: int | None = None) -> str:
    if names := list_entry.get("Names", []):
        return names[0]
    elif (id_ := list_entry.get("Id")) and isinstance(id_, str):
        if max_id_length:
            return id_[:max_id_length]
        else:
            return id_
    else:
        return "-"
