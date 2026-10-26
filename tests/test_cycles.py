from datetime import date

from app.cycles import cycle_for, cycle_label, next_cycle, previous_cycle


def test_on_payday_starts_new_cycle():
    assert cycle_for(date(2026, 10, 27), 27) == (date(2026, 10, 27), date(2026, 11, 27))


def test_day_before_payday_is_old_cycle():
    assert cycle_for(date(2026, 10, 26), 27) == (date(2026, 9, 27), date(2026, 10, 27))


def test_early_in_month_belongs_to_last_months_payday():
    assert cycle_for(date(2026, 11, 3), 27) == (date(2026, 10, 27), date(2026, 11, 27))


def test_crosses_year():
    assert cycle_for(date(2027, 1, 5), 27) == (date(2026, 12, 27), date(2027, 1, 27))


def test_payday_31_in_short_months():
    # No 30 or 31 Feb: the cycle starts on the last day of February
    assert cycle_for(date(2027, 2, 15), 31) == (date(2027, 1, 31), date(2027, 2, 28))
    assert cycle_for(date(2027, 2, 28), 31) == (date(2027, 2, 28), date(2027, 3, 31))


def test_payday_1_is_calendar_month():
    assert cycle_for(date(2026, 10, 15), 1) == (date(2026, 10, 1), date(2026, 11, 1))


def test_previous_and_next():
    start, end = cycle_for(date(2026, 11, 3), 27)
    assert previous_cycle(start, 27) == (date(2026, 9, 27), date(2026, 10, 27))
    assert next_cycle(end, 27) == (date(2026, 11, 27), date(2026, 12, 27))


def test_label():
    assert cycle_label(date(2026, 10, 27), date(2026, 11, 27)) == "27 Okt - 26 Nov 2026"
    assert (
        cycle_label(date(2026, 12, 27), date(2027, 1, 27))
        == "27 Des 2026 - 26 Jan 2027"
    )
