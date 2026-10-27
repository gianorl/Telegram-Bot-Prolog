"""Balances + transactions -> CSV file (opens in Excel, Google Sheets, Numbers).

A CSV holds one table, so the file has two sections, top to bottom:
balances (with a total), an empty row, then every transaction.

Pure functions: no Telegram, no database, so they're easy to test.
"""

import csv
import io

KIND_LABELS = {
    "expense": "Pengeluaran",
    "income": "Pemasukan",
    "transfer": "Pindah",
    "adjustment": "Penyesuaian",
    "lend": "Pinjamkan",
    "collect": "Dibayar balik",
    "borrow": "Pinjam",
    "repay": "Bayar hutang",
}

HEADER = [
    "Tanggal",
    "Jenis",
    "Item",
    "Kategori",
    "Dari akun",
    "Ke akun",
    "Orang",
    "Jumlah",
]


def safe_cell(value):
    """Formula injection guard. A cell starting with = + - @ would run as a
    formula in Excel (e.g. "=HYPERLINK(...)"). A leading ' keeps it as text."""
    text = "" if value is None else str(value)
    if text[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + text
    return text


def export_csv(balances, rows, tz, moment):
    """db.balances() + db.all_transactions() -> UTF-8 bytes of a CSV file.
    `moment` is when the export was made (shown above the balances)."""
    out = io.StringIO()
    writer = csv.writer(out)

    writer.writerow([f"Saldo per {moment.astimezone(tz):%Y-%m-%d %H:%M}"])
    writer.writerow(["Akun", "Saldo"])
    for b in balances:
        writer.writerow([safe_cell(b["name"]), b["balance"]])
    writer.writerow(["Total", sum(b["balance"] for b in balances)])
    writer.writerow([])

    writer.writerow(["Transaksi"])
    writer.writerow(HEADER)
    for t in rows:
        writer.writerow(
            [
                f"{t['created_at'].astimezone(tz):%Y-%m-%d %H:%M}",
                KIND_LABELS[t["kind"]],
                safe_cell(t["item"]),
                safe_cell(t["category"]),
                safe_cell(t["from_account"]),
                safe_cell(t["to_account"]),
                safe_cell(t["person"]),
                t["amount"],  # a plain number, so SUM() works in the sheet
            ]
        )
    # utf-8-sig adds a small marker at the start so Excel reads emoji and
    # accents correctly instead of showing garbage characters
    return out.getvalue().encode("utf-8-sig")
