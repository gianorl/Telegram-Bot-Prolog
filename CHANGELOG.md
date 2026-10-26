# Changelog

## v0.2.0 (R2: Real tracker), unreleased

### Added
- Accounts: `/akun` adds a bank, e-wallet, or cash with its current balance; `/saldo` shows every balance
- `/masuk` for income and `/pindah` for transfers between accounts (not counted as spending)
- `/catat` asks which account paid; most recently used account comes first
- Pay cycles from payday to payday (`PAYDAY_DAY` in `.env`)
- `/bulan`: in, out, difference, per category, budgets, vs last cycle, with ◀ ▶ buttons
- `/budget` per category per cycle; ⚠️ at 80%, 🚨 over budget, shown right after `/catat`
- Categories Tagihan and Hiburan
- `/riwayat`: browse all entries, edit name/amount/category/account, delete any entry
- `/sesuaikan`: match a balance to the real app (not counted as spending or income)
- `/hutang`: lend, collect, borrow, repay per person, with what's still open
- `/langganan`: recurring payments with a reminder on the due day (✅ Sudah bayar, ✏️ Jumlahnya beda, Lewati)

### Changed
- `/catat` asks the category first, then the item
- Categories have their own table; transactions, subscriptions and budgets point to it by id
- Storage moved from SQLite to PostgreSQL 18 (`DATABASE_URL` in `.env`, fresh schema; view it in DBeaver)
- Database tables: `transactions` (8 kinds, each with from/to account), `accounts`, `budgets`, `people`, `subscriptions`
- `/hapus` undoes the newest entry of any kind
- `/total` opens `/bulan`

### Removed
- `/total_by_category` (now part of `/bulan`)

## v0.1.0 (R1: Money core), 26 October 2026

### Added
- Owner-only access: anyone who is not `OWNER_ID` gets no reply (FR-01)
- `/start` and `/help`, and the `/` command menu set at startup (FR-05)
- `/hapus`: delete the last entry after confirming (FR-06)
- Hint to use `/help` for unknown text or commands (FR-07)
- `/catat` cancels itself after 5 minutes without a reply (BR-09)
- Item must be 1 to 100 characters, amount at most Rp100.000.000 (BR-03, BR-04)
- Error handler: crashes are logged and you get a short error message
- Database migrations with `PRAGMA user_version`
- Unit tests (`pytest`) and a manual Telegram checklist
- `requirements.txt`, `requirements-dev.txt`, `.env.example`, README

### Changed
- Code split from one `bot.py` into the `app/` package
- New records store the time you sent `/catat`, in WIB (`+07:00`), so late replies still log the right time
- `/total_by_category` lists the biggest category first

### Removed
- One-line entry (`makan 25000`): `/catat` is enough
