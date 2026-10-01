"""Calendar labels are fixed experiment inputs, never a moving wall-clock window."""

import re
from datetime import UTC, datetime


def month_index(month: str) -> int:
    if not re.fullmatch(r"(?!0000)\d{4}-(0[1-9]|1[0-2])", month):
        raise ValueError(f"Invalid calendar month: {month}")
    year, number = map(int, month.split("-"))
    return 12 * (year - 1) + number - 1


def add_month(month: str, offset: int) -> str:
    index = month_index(month) + offset
    if not 0 <= index < 9999 * 12:
        raise ValueError("Month arithmetic exceeds supported calendar")
    year, number = divmod(index, 12)
    return f"{year + 1:04d}-{number + 1:02d}"


def month_range(start: str, end: str) -> tuple[str, ...]:
    count = month_index(end) - month_index(start) + 1
    if count < 1:
        raise ValueError("Inverted month range")
    return tuple(add_month(start, i) for i in range(count))


def utc_month(timestamp: str) -> str:
    parsed = datetime.fromisoformat(timestamp)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("Timestamp requires an explicit timezone")
    return parsed.astimezone(UTC).strftime("%Y-%m")
