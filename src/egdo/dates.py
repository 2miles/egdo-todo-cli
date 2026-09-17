"""Parse scheduling expressions and format dates for terminal output."""

from __future__ import annotations

import calendar
from datetime import date, timedelta
import re


INVALID_MONTH_MESSAGE = (
    "Invalid month. Use YYYY-MM, MONTH, or MONTH YYYY, such as `jan 2026`."
)


def format_display_date(value: date) -> str:
    return f"{value.strftime('%a, %b')} {value.day}{ordinal_suffix(value.day)}"


def parse_future_date(value: str, today: date) -> date:
    """Resolve a supported date expression and require a date after ``today``."""
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


def parse_open_month(values: list[str], today: date) -> date:
    """Parse the friendly month forms accepted by ``egdo open``."""
    if not values:
        return today.replace(day=1)
    if len(values) == 1:
        iso_match = re.fullmatch(r"(\d{4})-(\d{2})", values[0])
        if iso_match:
            return _replace_month(today, int(iso_match[1]), int(iso_match[2]))
        month = _month_number(values[0])
        if month is not None:
            return today.replace(month=month, day=1)
    elif len(values) == 2:
        month = _month_number(values[0])
        if month is not None and re.fullmatch(r"\d{4}", values[1]):
            return _replace_month(today, int(values[1]), month)
    raise ValueError(INVALID_MONTH_MESSAGE)


def _month_number(value: str) -> int | None:
    normalized = value.casefold()
    for month in range(1, 13):
        if normalized in {
            calendar.month_abbr[month].casefold(),
            calendar.month_name[month].casefold(),
        }:
            return month
    return None


def _replace_month(today: date, year: int, month: int) -> date:
    try:
        return today.replace(year=year, month=month, day=1)
    except ValueError as exc:
        raise ValueError(INVALID_MONTH_MESSAGE) from exc


def parse_weekday_name(value: str) -> int | None:
    """Return a weekday number for an unambiguous full name or abbreviation."""
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
