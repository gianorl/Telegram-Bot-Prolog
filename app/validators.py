"""Business rules as pure functions: no Telegram, no database.

Each one returns the clean value or raises ValueError with a message
that the handler can send straight to the user.
"""

import re
from datetime import date, datetime, time

from app.formatters import rupiah

MAX_ITEM_LENGTH = 100
MAX_ACCOUNT_NAME_LENGTH = 30
MAX_AMOUNT = 100_000_000  # one transaction
MAX_BALANCE = 10_000_000_000  # an account's starting balance


def validate_item(text):
    item = (text or "").strip()
    if not item:
        raise ValueError("Nama tidak boleh kosong.")
    if len(item) > MAX_ITEM_LENGTH:
        raise ValueError(f"Maksimal {MAX_ITEM_LENGTH} karakter.")
    return item


def parse_amount(text, minimum=1, maximum=MAX_AMOUNT):
    cleaned = (text or "").strip()
    # isascii() too: isdigit() alone accepts "²" or "٣", which crash int()
    if not (cleaned.isascii() and cleaned.isdigit()):
        raise ValueError("Angka saja ya, contoh: 25000")
    amount = int(cleaned)
    if amount < minimum:
        raise ValueError("Jumlah harus lebih dari 0.")
    if amount > maximum:
        raise ValueError(f"Jumlah maksimal {rupiah(maximum)}.")
    return amount


def validate_account_name(text):
    name = (text or "").strip()
    if not name:
        raise ValueError("Nama akun tidak boleh kosong.")
    if len(name) > MAX_ACCOUNT_NAME_LENGTH:
        raise ValueError(f"Nama akun maksimal {MAX_ACCOUNT_NAME_LENGTH} karakter.")
    return name


def validate_person_name(text):
    name = (text or "").strip()
    if not name:
        raise ValueError("Nama tidak boleh kosong.")
    if len(name) > MAX_ACCOUNT_NAME_LENGTH:
        raise ValueError(f"Nama maksimal {MAX_ACCOUNT_NAME_LENGTH} karakter.")
    return name


def parse_day(text):
    """Day of the month for a recurring payment: 1 to 31."""
    cleaned = (text or "").strip()
    if not (cleaned.isascii() and cleaned.isdigit()) or not 1 <= int(cleaned) <= 31:
        raise ValueError("Tanggal 1 sampai 31 ya, contoh: 5")
    return int(cleaned)


# "4/11", "4/11/2026", "4/11 19:30", "4/11 19.30". ASCII: no "٤/١١"
WHEN = re.compile(
    r"^(\d{1,2})/(\d{1,2})(?:/(\d{4}))?(?:\s+(\d{1,2})[:.](\d{2}))?$", re.ASCII
)
DEFAULT_TIME = time(12, 0)  # no time typed: midday, so it stays on that day


def parse_when(text, now):
    """When something really happened -> datetime in now's timezone.

    No year: this year, or last year if that day hasn't come yet
    ("30/12" typed in January). Never in the future.
    """
    match = WHEN.match((text or "").strip())
    if not match:
        raise ValueError("Format: 4/11 atau 4/11 19:30")
    day, month, year, hour, minute = match.groups()

    try:
        picked = date(int(year) if year else now.year, int(month), int(day))
        if year is None and picked > now.date():
            picked = picked.replace(year=now.year - 1)
    except ValueError:  # 31/2, 13/1, or 29/2 in a year without it
        raise ValueError("Tanggal itu tidak ada.") from None
    if picked > now.date():
        raise ValueError("Tanggal tidak boleh di masa depan.")
    if picked.year < 2000:
        raise ValueError("Tahunnya terlalu lama.")

    if hour is None:
        # Today before 12:00: use right now instead of a time still to come
        return min(datetime.combine(picked, DEFAULT_TIME, now.tzinfo), now)
    if int(hour) > 23 or int(minute) > 59:
        raise ValueError("Jam 00:00 sampai 23:59 ya.")
    moment = datetime.combine(picked, time(int(hour), int(minute)), now.tzinfo)
    if moment > now:
        raise ValueError("Jam itu belum lewat.")
    return moment
