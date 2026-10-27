import csv
import io
from datetime import datetime
from zoneinfo import ZoneInfo

from app.export import HEADER, export_csv, safe_cell

JAKARTA = ZoneInfo("Asia/Jakarta")
MOMENT = datetime.fromisoformat("2026-10-27T11:00:00+00:00")  # 18:00 WIB
BALANCES = [
    {"name": "CIMB", "balance": 5_000_000},
    {"name": "GoPay", "balance": -20_000},
]


def row(**fields):
    base = {
        "created_at": datetime.fromisoformat("2026-10-27T03:30:00+00:00"),
        "kind": "expense",
        "item": "nasi padang",
        "category": "Makan",
        "from_account": "GoPay",
        "to_account": None,
        "person": None,
        "amount": 25000,
    }
    return base | fields


def read(data):
    assert data.startswith(b"\xef\xbb\xbf")  # BOM so Excel reads UTF-8
    return list(csv.reader(io.StringIO(data.decode("utf-8-sig"))))


def export(rows, balances=BALANCES):
    return read(export_csv(balances, rows, JAKARTA, MOMENT))


def transactions(lines):
    """The rows after the "Transaksi" header line."""
    return lines[lines.index(HEADER) + 1 :]


def test_balances_section_on_top_with_total():
    lines = export([])
    assert lines[:5] == [
        ["Saldo per 2026-10-27 18:00"],
        ["Akun", "Saldo"],
        ["CIMB", "5000000"],
        ["GoPay", "-20000"],
        ["Total", "4980000"],
    ]
    assert lines[5:7] == [[], ["Transaksi"]]


def test_header_and_one_row():
    lines = export([row()])
    # 03:30 UTC = 10:30 WIB; amount stays a plain number
    assert transactions(lines)[0] == [
        "2026-10-27 10:30",
        "Pengeluaran",
        "nasi padang",
        "Makan",
        "GoPay",
        "",
        "",
        "25000",
    ]


def test_kinds_get_indonesian_labels():
    first = transactions(export([row(kind="lend", person="Andi")]))[0]
    assert (first[1], first[6]) == ("Pinjamkan", "Andi")


def test_commas_and_quotes_stay_in_one_cell():
    assert transactions(export([row(item='kopi, "susu"')]))[0][2] == 'kopi, "susu"'


def test_account_names_are_guarded_too():
    lines = export([], balances=[{"name": "=cmd", "balance": 1}])
    assert lines[2] == ["'=cmd", "1"]


def test_formula_injection_is_neutralised():
    assert safe_cell('=HYPERLINK("http://evil")').startswith("'=")
    assert safe_cell("+62 812") == "'+62 812"
    assert safe_cell("-") == "'-"
    assert safe_cell("@SUM(A1)") == "'@SUM(A1)"
    assert safe_cell("nasi") == "nasi"
    assert safe_cell(None) == ""
