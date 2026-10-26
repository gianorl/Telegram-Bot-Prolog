import os
import sys
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    sys.exit("TELEGRAM_TOKEN belum diisi di .env")

# .env values are always strings; Telegram user ids are ints, and "123" != 123
raw_owner_id = os.getenv("OWNER_ID")
if not raw_owner_id:
    sys.exit("OWNER_ID belum diisi di .env (cek id kamu di @userinfobot)")
try:
    OWNER_ID = int(raw_owner_id)
except ValueError:
    sys.exit("OWNER_ID harus angka, contoh: 123456789")

# postgresql://user:password@host:5432/dbname. On the Mac, Homebrew's Postgres
# trusts your Mac user, so "postgresql:///prolog" (no user, no password) works.
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    sys.exit("DATABASE_URL belum diisi di .env, contoh: postgresql:///prolog")
TZ_NAME = os.getenv("TZ_NAME", "Asia/Jakarta")
TZ = ZoneInfo(TZ_NAME)

# Day of the month your salary arrives. Pay cycles (budgets, /bulan) start on it.
try:
    PAYDAY_DAY = int(os.getenv("PAYDAY_DAY", "1"))
except ValueError:
    sys.exit("PAYDAY_DAY harus angka 1 sampai 31")
if not 1 <= PAYDAY_DAY <= 31:
    sys.exit("PAYDAY_DAY harus angka 1 sampai 31")
