# Prolog: Technical Design (R1)

| | |
|---|---|
| Status | Draft v0.1 |
| Last updated | 26 October 2026 |
| Covers | R1: Telegram Bot, Money core |
| Product spec | `docs/PRD.md` (the "what"). This doc is the "how". |

---

## 1. Goals of this design
- Meet every R1 acceptance criterion and business rule in the PRD.
- Keep code small, readable, and testable without Telegram.
- Make it easy to add modules later (Reading, Fitness, ...) without rewriting.

## 2. Architecture

```
Telegram ──► bot.py (entry)
                │
                ├── auth guard (runs first, group -1) ── not owner? stop.
                │
                ├── handlers/common.py   /start /help, unknown input
                └── handlers/money.py    /catat flow, /total, /total_by_category, /hapus
                          │
                          ├── validators.py   (pure functions, no Telegram, no DB)
                          ├── formatters.py   (pure functions)
                          └── db.py           (all SQL lives here)
                                   │
                                   ▼
                               PostgreSQL (database "prolog")
```

**Layering rule:** handlers talk to Telegram and call the other layers. Handlers never write SQL. `validators.py` and `formatters.py` never import Telegram or the database. This keeps the important logic testable with plain `pytest`.

## 3. Project structure (target)

```
prolog/
├── bot.py                  # entry point: build app, register handlers, run polling
├── app/
│   ├── __init__.py
│   ├── config.py           # load .env, fail fast if a required value is missing
│   ├── auth.py             # owner-only guard
│   ├── db.py               # connection, migrations, queries
│   ├── validators.py       # parse_amount, validate_item, validate_category
│   ├── formatters.py       # rupiah, budget bars, transaction lines
│   ├── cycles.py           # pay cycle math (payday to payday)
│   └── handlers/
│       ├── __init__.py
│       ├── common.py       # /start, /help, unknown input, error handler
│       ├── shared.py       # helpers: keyboards, untrusted button parsing
│       ├── flows.py        # ONE ConversationHandler built from every module
│       ├── money.py        # /catat, /masuk, /pindah, /akun, /sesuaikan
│       ├── debts.py        # /hutang
│       ├── subscriptions.py # /langganan + reminder job
│       ├── history.py      # /riwayat: browse, edit, delete
│       └── reports.py      # /saldo, /bulan, /budget, /hapus
├── tests/
│   ├── test_validators.py
│   ├── test_formatters.py
│   └── test_db.py          # uses an in-memory SQLite database
├── docs/
│   ├── PRD.md
│   ├── TECH_DESIGN.md
│   └── issues/             # R1 task list (one file per GitHub issue)
├── requirements.txt
├── .env.example            # variable names only, no real values
├── CHANGELOG.md
├── CLAUDE.md
└── README.md
```

## 4. Configuration

| Variable | Required | Example | Notes |
|---|---|---|---|
| `TELEGRAM_TOKEN` | yes | `123456:ABC...` | Never print or log it |
| `OWNER_ID` | yes | `123456789` | My Telegram user ID (integer). Get it from a bot like @userinfobot |
| `DATABASE_URL` | yes | `postgresql:///prolog` | Postgres connection string. On the Mac no user/password is needed |
| `TZ_NAME` | no | `Asia/Jakarta` | Default `Asia/Jakarta` |
| `PAYDAY_DAY` | no | `27` | Day pay cycles start, 1 to 31. Default `1` (calendar month) |

`config.py` reads these once at startup. If `TELEGRAM_TOKEN` or `OWNER_ID` is missing or invalid, the bot exits with a clear message (PRD FR-01).

## 5. Owner-only access (BR-01, FR-01)

Use a guard handler that runs **before every other handler**, for every kind of update (messages, commands, button taps):

- Register a `TypeHandler(Update, owner_guard)` in **group -1**.
- `owner_guard` checks `update.effective_user.id == OWNER_ID`.
- If it does not match, raise `ApplicationHandlerStop`. Nothing else runs, nothing is saved, no reply is sent.

Why a global guard instead of a filter on each handler: one place to get right, and it also covers button taps (`CallbackQueryHandler`), which a per-handler message filter can miss.

## 6. Data

### Schema (version 4, R2.5)
Version 4 rebuilds `transactions` with `from_account_id` / `to_account_id` / `person_id` and the kinds expense, income, transfer, adjustment, lend, collect, borrow, repay. It adds `people` and `subscriptions`. R2 income rows move their account to `to_account_id`.

#### Version 3 (R2), kept for history
See PRD §10 for the diagram. Tables: `accounts`, `transactions` (kind = expense / income / transfer), `budgets`.
Migration 3 copies R1 `expenses` rows into `transactions` (no account) and drops `expenses`.
`PRAGMA foreign_keys = ON` is set on every connection.

Balance of an account (BR-14), computed in SQL by `db.balances()`:
```
opening_balance
+ income into it
− expenses from it
− transfers out of it
+ transfers into it
```

Reports take a pay cycle as `[start, end)` ISO strings with `+07:00`. `created_at` is `TIMESTAMPTZ`, so Postgres compares real moments in time, and returns them as Jakarta-time `datetime` objects.

### Migrations
A `schema_version` table remembers which migrations ran:

- Read `MAX(version)` from `schema_version`.
- Run each migration whose number is higher, in order, each inside one transaction, then insert its number.
- Migrations are a numbered list in `db.py`. Each one runs exactly once per database.
- Postgres can undo DDL (`CREATE TABLE`) in a transaction, so a failed migration leaves nothing half-done.

This scales to future modules (new tables) and is safe to run on every startup.

### Queries (all in `db.py`)
- accounts: `add_account`, `find_account`, `get_account`, `accounts()` (most recently used first), `balances()`
- transactions: `add_transaction(kind, item, amount, created_at, category, account_id, to_account_id)`, `last_transaction()`, `delete_transaction(id)`
- reports: `sum_by_kind(kind, start, end)`, `spending_by_category(start, end)`, `spent_in_category(category, start, end)`
- budgets: `set_budget` (insert or update), `delete_budget`, `budgets()`

All queries use `?` placeholders. Commit after every write.

### Time (BR-07)
Use the time the `/catat` message was **sent** (`update.message.date`, which Telegram gives in UTC), converted with `.astimezone(ZoneInfo(TZ_NAME))`. Store with `.isoformat()` so the `+07:00` offset is saved.

Why sent time and not `datetime.now()`: while the bot is offline, Telegram holds messages for up to 24 hours. When the bot comes back it processes them late, and `now()` would record the wrong time.

## 7. Conversation flow `/catat`

```
/catat ──► ITEM ──(text, validated)──► CATEGORY ──(button, validated)──► AMOUNT ──(valid)──► save, END
             │                           │                                 │
             └────── /batal or 5 min no reply at any step ──► cancel, nothing saved
```

- Validation errors keep the user on the same step (return the same state).
- Timeout (BR-09): `ConversationHandler(conversation_timeout=300)`. This needs the job queue, so install `python-telegram-bot[job-queue]`.
- `context.user_data` is cleared on save, cancel, and timeout.

## 8. Validation (pure functions in `validators.py`)

| Function | Rule | Returns |
|---|---|---|
| `validate_item(text)` | trimmed, 1 to 100 chars (BR-04) | cleaned text, or raises `ValueError` with a user-facing message |
| `parse_amount(text)` | digits only, 1 to 100.000.000 (BR-02, BR-03) | `int`, or raises `ValueError` |
| `validate_category(value)` | must be in `CATEGORIES` (BR-05) | value, or raises `ValueError` |

Handlers catch `ValueError` and reply with its message. This makes every rule a one-line unit test.

## 9. Errors and logging
- Use Python's `logging` module, level INFO.
- **Set the `httpx` logger to WARNING.** At INFO, it logs request URLs, and Telegram request URLs contain the bot token.
- Register an error handler (`app.add_error_handler`) that logs the exception and replies with a short generic message, so the bot never goes silent on a crash.
- Never log message contents in production logs beyond what is needed to debug.

## 10. Testing

| Layer | How | Covers |
|---|---|---|
| validators, formatters | `pytest`, plain function calls | BR-02 to BR-05, BR-11 |
| db | `pytest` against a local `prolog_test` Postgres database, wiped before each test (`tests/conftest.py` refuses any name not ending in `_test`) | migrations, totals, empty table, delete |
| handlers / flows | manual checklist from PRD acceptance criteria, run in Telegram | FR-01 to FR-07 |

Rule: every acceptance criterion maps to either a unit test or a line in the manual checklist.

## 11. Dependencies
- `python-telegram-bot[job-queue]` (pin the version in `requirements.txt`)
- `python-dotenv`
- `psycopg[binary]` + `psycopg-pool` (PostgreSQL driver and connection pool)
- Dev: `pytest`, `ruff`

## 12. Decisions (short records)

| # | Decision | Why | Alternative considered |
|---|---|---|---|
| D1 | SQLite (replaced by D18) | One file, built into Python, zero setup, fine for one user | Google Sheets (formula injection risk, API setup) |
| D2 | Polling for R1 | Runs on a laptop with no public URL | Webhook (needed later for 24/7 hosting, R6) |
| D3 | Single owner, no `user_id` column | Prolog is for me only (PRD) | Multi-user schema (unneeded complexity) |
| D4 | Raw `sqlite3`, no ORM | Learn SQL directly, small app | SQLAlchemy (more abstraction to learn) |
| D5 | Global owner guard in group -1 | One place, covers button taps too | Filters on every handler |
| D6 | `PRAGMA user_version` migrations (replaced by `schema_version` table, D18) | Simple, built in, scales to new tables | try/except ALTER (fragile), Alembic (overkill) |
| D7 | Drop one-line entry `makan 25000` | `/catat` is enough; no clash with the unknown-input hint | Keep as a fast path (R1-12) |
| D8 | Bot menu set in code with `set_my_commands` at startup | `/help` and the `/` menu share one list in `handlers/common.py`, never out of sync | BotFather `/setcommands` by hand |
| D9 | Button data has a prefix (`cat:Makan`, `hapus:42`, `hapus:batal`) | Each handler only picks up its own buttons; old buttons get a "tidak berlaku" toast | Plain values (`Makan`), which any callback handler could catch |
| D10 | One `transactions` table with `kind` (expense, income, transfer) | Balances and reports are one query each; `/hapus` works on any kind | Separate tables per kind (every report needs a UNION) |
| D11 | All flows in ONE ConversationHandler (`handlers/money.py: flows`) | Starting `/masuk` in the middle of `/catat` replaces it cleanly; separate handlers could both be "active" and fight over the next message | One ConversationHandler per flow |
| D12 | Pay cycles as pure functions in `app/cycles.py`, `PAYDAY_DAY` in `.env` | Easy to test (edge cases: payday 31, year change) | Calendar months (don't match when salary arrives) |
| D13 | Balances are computed, never stored | Can't drift out of sync; deleting a transaction fixes the balance automatically | A `balance` column updated on every write |
| D14 | Every transaction has `from_account_id` and `to_account_id` | One balance rule for all 8 kinds; new kinds need no new balance logic | A CASE per kind in the balance query (grew with every feature) |
| D15 | Subscription reminders: a check every 30 min + at startup, `last_reminded` per month | The laptop is often asleep; a missed fixed-time alarm would never fire. Remembering the month prevents duplicates | One `run_daily` alarm at 08:00 |
| D16 | Flow modules export `ENTRY_POINTS` + `STATES` (string names); `flows.py` merges them | New modules plug in without touching others; string states can't collide | Shared integer `range()` states |
| D17 | Editable fields map to fixed SQL strings (`db._UPDATE_SQL`) | Column names can't be `?` placeholders; a whitelist keeps user input out of SQL text | f-string with the column name (SQL injection risk) |
| D18 | PostgreSQL 18 with raw `psycopg` 3 and a small pool, autocommit | A real server: browse live in DBeaver, the API and bot can share it, and the VPS can host it. Postgres rejects bad data and needs less RAM than MySQL on a 2 GB VPS. Real data was empty, so we started with a fresh schema | MySQL (common in Indonesian jobs, more RAM); stay on SQLite (can't be browsed remotely) |
| D19 | `categories` table; `category_id` FK in transactions, subscriptions, budgets; CHECK that every expense has one | Rename in one place, Postgres rejects unknown ids, ready for a manage-categories screen in R3. Buttons send `cat:<id>` | Fixed Python list + text column (simpler, but only Python guarded it) |

## 13. Build order for R1
See `docs/issues/`. Order: refactor with no behavior change first, then the owner guard, then features, then tests and release.

## 14. Risks
| Risk | Mitigation |
|---|---|
| Token leak via logs | `httpx` logger at WARNING, never log config |
| Data loss on laptop | Weekly `pg_dump prolog > backups/prolog-DATE.sql` until the VPS adds automatic backups |
| Refactor breaks the bot | Refactor in small steps, run the manual checklist after each |
