import pytest

from app.validators import (
    parse_amount,
    parse_day,
    validate_account_name,
    validate_item,
    validate_person_name,
)

# ---------- BR-04: item ----------


def test_item_is_trimmed():
    assert validate_item("  kopi susu  ") == "kopi susu"


def test_item_100_chars_ok():
    assert validate_item("a" * 100) == "a" * 100


@pytest.mark.parametrize("text", ["", "   ", None, "a" * 101])
def test_item_invalid(text):
    with pytest.raises(ValueError):
        validate_item(text)


# ---------- BR-02, BR-03: amount ----------


@pytest.mark.parametrize(
    "text, expected",
    [("25000", 25000), (" 25000 ", 25000), ("1", 1), ("100000000", 100_000_000)],
)
def test_amount_valid(text, expected):
    assert parse_amount(text) == expected


@pytest.mark.parametrize(
    "text",
    ["0", "-5", "abc", "25rb", "25.000", "25,000", "1.5", "", "²", "100000001"],
)
def test_amount_invalid(text):
    with pytest.raises(ValueError):
        parse_amount(text)


def test_starting_balance_allows_zero_and_big_numbers():
    assert parse_amount("0", minimum=0, maximum=10_000_000_000) == 0
    assert parse_amount("250000000", minimum=0, maximum=10_000_000_000) == 250_000_000


# ---------- accounts ----------


def test_account_name():
    assert validate_account_name("  SeaBank ") == "SeaBank"
    with pytest.raises(ValueError):
        validate_account_name("")
    with pytest.raises(ValueError):
        validate_account_name("x" * 31)


@pytest.mark.parametrize("text, expected", [("1", 1), (" 5 ", 5), ("31", 31)])
def test_day_valid(text, expected):
    assert parse_day(text) == expected


@pytest.mark.parametrize("text", ["0", "32", "-1", "lima", "", "²"])
def test_day_invalid(text):
    with pytest.raises(ValueError):
        parse_day(text)


def test_person_name():
    assert validate_person_name(" Andi ") == "Andi"
    with pytest.raises(ValueError):
        validate_person_name("  ")
