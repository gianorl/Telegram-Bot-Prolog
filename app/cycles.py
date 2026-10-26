"""Pay cycles: from payday to the day before the next payday.

Pure functions (no Telegram, no database), so they're easy to test.
Example with payday 27: 27 Okt - 26 Nov is one cycle.
"""

import calendar
from datetime import date, timedelta

MONTHS = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "Mei",
    "Jun",
    "Jul",
    "Agu",
    "Sep",
    "Okt",
    "Nov",
    "Des",
]


def _payday_in(year, month, payday):
    # Payday 31 in a 30-day month (or February) falls on the last day instead
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(payday, last_day))


def _add_months(year, month, delta):
    index = year * 12 + (month - 1) + delta
    return index // 12, index % 12 + 1


def cycle_for(day, payday):
    """The cycle that contains `day`, as (start, end). `end` is NOT included."""
    payday_this_month = _payday_in(day.year, day.month, payday)
    if day >= payday_this_month:
        start = payday_this_month
    else:
        start = _payday_in(*_add_months(day.year, day.month, -1), payday)
    end = _payday_in(*_add_months(start.year, start.month, 1), payday)
    return start, end


def previous_cycle(start, payday):
    return cycle_for(start - timedelta(days=1), payday)


def next_cycle(end, payday):
    return cycle_for(end, payday)


def cycle_label(start, end):
    """(27 Okt 2026, 27 Nov 2026) -> "27 Okt - 26 Nov 2026" """
    last = end - timedelta(days=1)
    first = f"{start.day} {MONTHS[start.month - 1]}"
    if start.year != last.year:
        first += f" {start.year}"
    return f"{first} - {last.day} {MONTHS[last.month - 1]} {last.year}"
