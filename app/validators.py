"""Business rules as pure functions: no Telegram, no database.

Each one returns the clean value or raises ValueError with a message
that the handler can send straight to the user.
"""

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
