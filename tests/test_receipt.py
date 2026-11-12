"""parse_receipt on real Tesseract output (--psm 6).

Each sample is OCR text exactly as Tesseract gave it, mistakes included.
Personal data (names, phone, address, order numbers) is removed or masked:
this repo is public. When the bot misreads a receipt, its text goes here.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from app.receipt import parse_receipt

JKT = ZoneInfo("Asia/Jakarta")
NOW = datetime(2026, 11, 11, 20, 0, tzinfo=JKT)

# Fictional receipt, phone-photo version after clean_receipt.py
DUMMY_CLEANED = """\
WARUNG PRORATE
JL. Kalimalang No. 12
Bekasi Timur
04/11/2026 19:32 Kasir: Ani
Hasi Goreng Spesial 25.600
Es Teh Manis 2x 3.000
Kerupuk 3.600
Ayam Bakar 22.006
SUBTOTAL 58,000
PPN 13% 6.380
TOTAL 64, 380
TUNAI 100. 000
KEMBALI 35.628
Terima kasih, datang tagi'
"""

# Same fictional receipt, phone photo, NOT cleaned
DUMMY_MESSY = """\
WARUNG PRORATE
Ji. Kalimalang No. 12
Bekasi Timur
Bea er aan
| 04/11/2026 19:32 Kasir: Ani
opin Saal am TS
Masi Goreng Spesial 25.000
fs Teh Manis 2% 3.000 |
| kerupuk 3.000 i
3 Ayam Bakar 22.000 7
SUBTOTAL a
PPN 11%, 6,380
TOTAL 64,300
"""

# Astro invoice screenshot, enlarged 3x. Ends at the subtotal: no fees.
ASTRO_INVOICE = """\
22:18 © ON nil CD 4
09 Nov 2026 @
INV/AS/xxxx ASTRO Lf
Detail Penerima
Detail Pesanan
Men's Biore Acne Cleanse Body Wash Refill 400ml 1 Rp32.100 Rp32.100
Fiesta Chicken Karage 400gram 1 Rp46.000 Rp46.000
Skippy Chunky Peanut Butter Spread 500gram 1 Rp67.500 Rp67.500
Total Harga Barang Rp226.176
"""

# Astro order status screenshot, enlarged 3x. Has the real total.
ASTRO_STATUS = """\
22:24 © ON il G4
esanan
< Status P PT
#xxxxxxxx
Pengiriman CS 15 - 30 menit
1x Men's Biore Acne Cleanse Body Wash Refill Rp32.100
lx Fiesta Chicken Karage 400gram Rp46.000
{Rp9-900}
Permen 22gram (Rp18-300)
1x Skippy Chunky Peanut Butter Spread Rp67.500
Beri ulasan produk
4 ™ Bagaimana pesananmu?
09 Nov, 22.11
Total Harga Barang Rp245-000 Rp226.176
Total Biaya Layanan @ Rp3.500
Total Ongkir Rp15-690 Rp5.000
GRATISONGKIR -Rp5.000
Total Rp229.676
Ajukan Komplain
"""


def test_dummy_cleaned():
    assert parse_receipt(DUMMY_CLEANED, NOW) == {
        "name": None,  # not a store in KNOWN_STORES
        "when": datetime(2026, 11, 4, 19, 32, tzinfo=JKT),
        "total": 64380,  # "64, 380": not SUBTOTAL, not TUNAI
    }


def test_dummy_messy_reads_wrong_total_that_looks_right():
    # Printed 64.380. No rule can know: this is why the bot asks "Benar?"
    assert parse_receipt(DUMMY_MESSY, NOW)["total"] == 64300


def test_dummy_messy_date_survives_junk_at_line_start():
    assert parse_receipt(DUMMY_MESSY, NOW)["when"] == datetime(
        2026, 11, 4, 19, 32, tzinfo=JKT
    )


def test_astro_invoice_has_no_total_only_subtotal():
    assert parse_receipt(ASTRO_INVOICE, NOW) == {
        "name": "Astro",
        "when": datetime(2026, 11, 9, 12, 0, tzinfo=JKT),  # no time -> 12:00
        "total": None,  # "Total Harga Barang" misses the Rp3.500 fee
    }


def test_astro_status():
    assert parse_receipt(ASTRO_STATUS, NOW) == {
        "name": None,  # "Astro Care" in the header was lost by OCR
        "when": datetime(2026, 11, 9, 22, 11, tzinfo=JKT),  # no year -> 2026
        "total": 229676,  # "Total", not "Total Harga Barang", not "Rp245-000"
    }


def test_minutes_are_not_a_date():
    assert parse_receipt("Pengiriman 15 - 30 menit", NOW)["when"] is None


def test_future_date_is_ignored():
    assert parse_receipt("25/12/2026 10:00", NOW)["when"] is None


def test_nothing_found():
    assert parse_receipt("", NOW) == {"name": None, "when": None, "total": None}
