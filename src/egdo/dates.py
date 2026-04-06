from __future__ import annotations

from datetime import date, timedelta


def format_display_date(value: date) -> str:
    return f"{value.strftime('%a, %b')} {value.day}{ordinal_suffix(value.day)}"


def parse_future_date(value: str, today: date) -> date:
    token = value.strip()
    if not token:
        raise ValueError("Move date cannot be empty")

    lowered = token.lower()
    if lowered == "tomorrow":
        return today + timedelta(days=1)

    if lowered.startswith("+"):
        try:
            days = int(lowered[1:])
        except ValueError as exc:
            raise ValueError(f"Invalid relative date: {value}") from exc
        if days <= 0:
            raise ValueError("Relative move date must be at least +1")
        return today + timedelta(days=days)

    weekday = parse_weekday_name(lowered)
    if weekday is not None:
        days_ahead = (weekday - today.weekday()) % 7
        if days_ahead == 0:
            days_ahead = 7
        return today + timedelta(days=days_ahead)

    try:
        parsed = date.fromisoformat(token)
    except ValueError as exc:
        raise ValueError(
            "Invalid move date. Use tomorrow, +N, weekday name, or YYYY-MM-DD."
        ) from exc
    if parsed <= today:
        raise ValueError("Move destination must be a future date")
    return parsed


def parse_weekday_name(value: str) -> int | None:
    weekday_names = {
        "monday": 0,
        "mon": 0,
        "tuesday": 1,
        "tue": 1,
        "tues": 1,
        "wednesday": 2,
        "wed": 2,
        "thursday": 3,
        "thu": 3,
        "thurs": 3,
        "friday": 4,
        "fri": 4,
        "saturday": 5,
        "sat": 5,
        "sunday": 6,
        "sun": 6,
    }
    return weekday_names.get(value)


def ordinal_suffix(day: int) -> str:
    if 11 <= day % 100 <= 13:
        return "th"
    return {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
