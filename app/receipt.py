"""Turn OCR text from a receipt or payment screenshot into name, date and total.

Pure function: no Telegram, no database, no Tesseract. OCR text goes in,
a dict comes out. Anything not found is None, and the bot asks for it:
"I don't know" is better than a confident wrong answer.
"""

import re

from app.validators import MAX_AMOUNT, parse_when

# Stores you actually use. Add one each time a receipt's name isn't found.
KNOWN_STORES = ["Astro", "Indomaret", "Alfamart", "Gacoan"]

# "04/11/2026 19:32", "04/11/2026"
SLASH_DATE = re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4})(?:\s+(\d{1,2})[:.](\d{2}))?\b")

# "09 Nov 2026", "09 Nov, 22.11", "4 Oktober 2026 08:05"
MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "mei": 5, "may": 5, "jun": 6,
    "jul": 7, "agu": 8, "aug": 8, "sep": 9, "okt": 10, "oct": 10, "nov": 11,
    "des": 12, "dec": 12,
}
WORD_DATE = re.compile(
    r"\b(\d{1,2})\s+([a-z]{3})[a-z]*\.?(?:\s+(\d{4}))?(?:,?\s+(\d{1,2})[:.](\d{2}))?\b",
    re.IGNORECASE,
)

# Which line holds what you paid, best first. Each must START the line.
# Never a subtotal ("SUBTOTAL", "Total Harga Barang"): it misses fees and
# discounts, so a wrong number would look right.
TOTAL_LABELS = [
    re.compile(r"^total\s+pembayaran\b", re.IGNORECASE),
    re.compile(r"^total\s+bayar\b", re.IGNORECASE),
    re.compile(r"^grand\s+total\b", re.IGNORECASE),
    # "TOTAL" alone, right before the number: not "Total Hemat", "Total Item"
    re.compile(r"^total\s*:?\s*(rp)?\s*\d", re.IGNORECASE),
]

# "229.676", "64,380", "64, 380" (OCR adds spaces), "5000"
MONEY = re.compile(r"\d{1,3}(?:[.,]\s?\d{3})+|\d+")


def parse_receipt(text, now):
    """OCR text -> {"name": str|None, "when": datetime|None, "total": int|None}."""
    lines = [_clean(line) for line in (text or "").splitlines()]
    lines = [line for line in lines if line]
    return {
        "name": _find_name(lines),
        "when": _find_when(lines, now),
        "total": _find_total(lines),
    }


def _clean(line):
    """OCR leaves junk at the edges: "| 04/11/2026 19:32" -> "04/11/2026 19:32"."""
    return re.sub(r"^[^A-Za-z0-9]+", "", line).strip()


def _find_name(lines):
    for store in KNOWN_STORES:
        word = re.compile(rf"\b{store}\b", re.IGNORECASE)
        if any(word.search(line) for line in lines):
            return store
    return None


def _find_when(lines, now):
    """First date that parse_when accepts. Reusing it gives the same rules
    as typing a date: no time -> 12:00, no year -> this year, never future."""
    for line in lines:
        for typed in _dates_in(line):
            try:
                return parse_when(typed, now)
            except ValueError:
                continue  # "31/02/2026", or OCR misread "04" as "84"
    return None


def _dates_in(line):
    """Every date in the line, rewritten the way parse_when wants: "9/11/2026 22:11"."""
    for day, month, year, hour, minute in SLASH_DATE.findall(line):
        yield _as_typed(day, month, year, hour, minute)
    for day, month_word, year, hour, minute in WORD_DATE.findall(line):
        month = MONTHS.get(month_word.lower())
        if month:  # "15 menit" is not a date
            yield _as_typed(day, month, year, hour, minute)


def _as_typed(day, month, year, hour, minute):
    typed = f"{int(day)}/{month}"
    if year:
        typed += f"/{year}"
    if hour:
        typed += f" {hour}:{minute}"
    return typed


def _find_total(lines):
    for label in TOTAL_LABELS:
        for line in lines:
            if label.search(line):
                return _last_amount(line)
    return None


def _last_amount(line):
    """The LAST number: a crossed-out old price comes first ("Rp245-000 Rp226.176")."""
    numbers = MONEY.findall(line)
    if not numbers:
        return None
    amount = int(re.sub(r"[.,\s]", "", numbers[-1]))
    return amount if 0 < amount <= MAX_AMOUNT else None
