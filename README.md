# Prolog

Personal life-logging Telegram bot ("Pro" + "log"). One owner, many small modules.
Module 1 is a **money tracker**: every account (bank, e-wallet, cash), spending, income,
transfers, budgets, and a report per pay cycle (payday to payday).

## Commands

| Command | What it does |
|---|---|
| `/akun` | Add an account (CIMB, SeaBank, GoPay, Cash…) with its current balance |
| `/catat` | Spending: category → item → account → amount |
| `/masuk` | Income: item → account → amount |
| `/pindah` | Move money between accounts (top-up, cash withdrawal). Not counted as spending |
| `/saldo` | Balance of every account + total |
| `/bulan` | This pay cycle: in, out, per category, budgets, vs last cycle (◀ ▶ to browse) |
| `/budget` | `/budget Makan 1500000` to set, `/budget Makan 0` to remove, `/budget` to see bars |
| `/riwayat` | Browse every entry; tap one to edit or delete it |
| `/ekspor` | Download current balances + every transaction as a CSV file (Excel, Google Sheets) |
| `/hutang` | Who owes whom: lend, get paid back, borrow, pay back |
| `/langganan` | Recurring payments (Netflix, kos, cicilan): reminder on the due day, one tap to log |
| `/sesuaikan` | Real app shows a different balance? Type the real one, the difference is recorded |
| `/hapus` | Delete the last entry (asks first) |
| `/batal` | Cancel the flow in progress |
| `/help` | List the commands |

Only the owner (`OWNER_ID`) can use the bot. Everyone else gets no reply.

## Setup (macOS / Linux)

```bash
git clone git@github.com:gianorl/Telegram-Bot-Prolog.git
cd Telegram-Bot-Prolog
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

# PostgreSQL (macOS, Homebrew)
brew install postgresql@18
brew services start postgresql@18
$(brew --prefix postgresql@18)/bin/createdb prolog
$(brew --prefix postgresql@18)/bin/createdb prolog_test   # tests wipe this one
```

Fill in `.env`:
- `TELEGRAM_TOKEN`: from @BotFather
- `OWNER_ID`: your Telegram user id, from @userinfobot
- `PAYDAY_DAY`: the day your salary arrives (1 to 31). Pay cycles start on it
- `DATABASE_URL`: `postgresql:///prolog` on the Mac. Tables are created on first start

View the data in DBeaver: New Connection → PostgreSQL, host `localhost`, port `5432`, database `prolog`, user = your Mac username, no password.

Run it:

```bash
python bot.py      # stop with Ctrl + C
```

## Development

```bash
pip install -r requirements-dev.txt
pytest             # unit tests (needs the prolog_test database)
ruff check .       # lint
```

Flows inside Telegram are checked by hand with `docs/MANUAL_TEST.md`.

## Docs
- `docs/PRD.md`: what the product does (rules, acceptance criteria, release plan)
- `docs/TECH_DESIGN.md`: how it is built
- `CHANGELOG.md`: what changed per version

## Project layout

```
bot.py                 entry point: build app, register handlers, run
app/config.py          reads .env, exits early if something is missing
app/auth.py            owner-only guard
app/db.py              PostgreSQL: connection pool, migrations, all queries
app/validators.py      business rules (pure functions)
app/formatters.py      Rp formatting, budget bars
app/cycles.py          pay cycle math
app/handlers/common.py /start, /help, unknown input, errors
app/handlers/flows.py  one conversation for every multi-step flow
app/handlers/shared.py helpers: keyboards, button parsing
app/handlers/money.py  /catat, /masuk, /pindah, /akun, /sesuaikan
app/handlers/debts.py  /hutang
app/handlers/subscriptions.py /langganan + reminders
app/handlers/history.py /riwayat
app/handlers/reports.py /saldo, /bulan, /budget, /hapus
tests/                 pytest
```
