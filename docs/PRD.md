# Prolog: Product Requirements Document (PRD)

| | |
|---|---|
| Owner | Fergiant Shihab |
| Status | Draft v0.1 |
| Last updated | 26 October 2026 |
| Current release | R2.5: Real tracker + history, adjustments, debts, subscriptions |

---

## 1. Vision

Prolog ("Pro" + "log") is my personal life-logging system. It is one place where I record the small things that matter in my life (money, reading, body, people, habits) so I can look back and **see my own progress**, instead of feeling stuck.

Prolog is built for **one user: me**, forever. It is not a public product.

## 2. End goals

1. **Personal:** log my daily life in seconds, and get a weekly recap that shows I am moving forward.
2. **Money:** know exactly where my money goes each month, and stop being surprised by bills.
3. **Learning:** build and understand every line of my first own app, end to end (bot, database, deployment, testing).
4. **Content:** document the build as a series for Prorate ("Programmer Rada Telat").
5. **Portfolio:** a clean public repo (code only, never data) that shows I can ship.

## 3. Problem

- I don't track spending consistently, so money feels out of control.
- Notes from books and life events get lost, so I forget what I learned.
- I can't see progress over time, which makes me feel stuck.
- Existing apps are either too heavy to use daily, or not shaped around my life.

## 4. User

| | |
|---|---|
| User | Me only (single owner) |
| Device | Phone (Telegram), laptop for development |
| Context | Logging happens on the go (warung, commute, office), so input must take seconds |
| Language | Bot replies in Bahasa Indonesia |

## 5. Product shape

```
Me (Telegram app)
   │
   ▼
Telegram server  ──►  Prolog bot (Python)  ──►  PostgreSQL
                          │
                          └── modules: Money (now), Reading, Fitness, Journal, ...
```

- **Interface now:** Telegram bot.
- **Interface later:** Telegram Mini App for dashboards. Native Android only if Telegram can't do something I really need.
- The backend and database stay the same when the interface changes.

---

## 6. Scope of the current release (R1: Money core)

### In scope
- Owner-only access
- Guided expense entry: `/catat`
- Cancel entry: `/batal`
- Totals: `/total`, `/total_by_category`
- `/start` and `/help`
- Undo the last entry: `/hapus`
- Data saved in SQLite

### Out of scope (for R1)
- Receipt photos, OCR, monthly reports, reminders (later releases)
- Other modules (Reading, Fitness, Journal, People, Ibadah)
- Mini App, Android
- Multi-user support
- Bank or e-wallet integration
- Running 24/7 on a server (R1 runs on my laptop)

---

## 7. Business rules

| ID | Rule |
|---|---|
| BR-01 | **Single owner.** Only my Telegram user ID (stored as `OWNER_ID` in `.env`) can use the bot. Messages from anyone else are ignored and never written to the database. |
| BR-02 | **Currency.** All amounts are Indonesian Rupiah, whole numbers only (no decimals). |
| BR-03 | **Valid amount.** Amount must be an integer greater than 0 and at most Rp100.000.000. |
| BR-04 | **Valid item.** Item name is required, 1 to 100 characters, trimmed of spaces. |
| BR-05 | **Fixed categories.** Category must be one of: Makan, Transport, Belanja, Tagihan, Hiburan, Lainnya (Tagihan and Hiburan added in R2). Any other value is rejected, including forged button data. |
| BR-06 | **Default category.** Records without a category are counted as Lainnya. |
| BR-07 | **Timestamps.** Every record stores the time I sent `/catat`, in Asia/Jakarta time (WIB). |
| BR-08 | **Undo and edit.** `/hapus` removes the most recent record after confirmation. Since R2.5, any record can be edited or deleted (with confirmation) from `/riwayat`. |
| BR-09 | **Abandoned entry.** An unfinished `/catat` flow is cancelled after 5 minutes of no reply, and nothing is saved. |
| BR-10 | **Privacy.** Data stays in my own Postgres database (my Mac, later my VPS), never reachable from the public internet. The database and `.env` are never committed to Git. |
| BR-11 | **Display format.** Amounts are shown as `Rp25.000` (dot as thousands separator). |

---

## 8. Functional requirements and acceptance criteria

Status: ✅ done, 🟡 partial, ⬜ not started

### FR-01 Owner-only access ✅
- **Given** a Telegram user whose ID is not `OWNER_ID`, **when** they send any message or command, **then** the bot does not reply and nothing is saved.
- **Given** I am the owner, **when** I use any command, **then** it works normally.
- **Given** `OWNER_ID` is missing from `.env`, **when** the bot starts, **then** it stops with a clear error message.

### FR-02 Guided expense entry `/catat` ✅
- **Given** I send `/catat`, **then** the bot asks "Apa yang kamu beli?" ✅
- **Given** I send an item name, **then** the bot shows category buttons (Makan, Transport, Belanja, Lainnya). ✅
- **Given** I tap a category, **then** the bot asks for the amount. ✅
- **Given** the category data is not in the list (forged), **then** the bot rejects it and shows the buttons again. ✅
- **Given** I send a non-number amount (for example `abc`, `25rb`, `25.000`), **then** the bot asks again and stays on the amount step. ✅
- **Given** I send `0` or a negative number, **then** the bot rejects it. ✅
- **Given** I send more than Rp100.000.000, **then** the bot rejects it. ✅
- **Given** an item name over 100 characters, **then** the bot rejects it and asks again. ✅
- **Given** a valid amount, **then** the record is saved and the bot replies `✅ <item> (<category>) Rp<amount>`. ✅
- **Given** I don't reply for 5 minutes, **then** the flow is cancelled and nothing is saved. ✅

### FR-03 Cancel `/batal` ✅
- **Given** I am in the middle of `/catat`, **when** I send `/batal`, **then** the bot replies "Dibatalkan." and nothing is saved.

### FR-04 Totals ✅ (replaced in R2: `/total` now opens `/bulan`, `/total_by_category` is removed)
- **Given** records exist, **when** I send `/total`, **then** the bot replies with the sum of all amounts, for example `Total: Rp43.000`.
- **Given** no records exist, **when** I send `/total`, **then** the bot replies `Total: Rp0`.
- **Given** records exist, **when** I send `/total_by_category`, **then** the bot replies one line per category with its sum.
- **Given** no records exist, **when** I send `/total_by_category`, **then** the bot replies "Belum ada catatan pengeluaran."

### FR-05 Start and help ✅
- **Given** I send `/start` or `/help`, **then** the bot lists all commands with a one-line description each.
- Commands are registered in BotFather (`/setcommands`) so they appear in the `/` menu.

### FR-06 Undo last entry `/hapus` ✅
- **Given** records exist, **when** I send `/hapus`, **then** the bot shows the last record with buttons "Ya, hapus" and "Batal".
- **Given** I tap "Ya, hapus", **then** that record is deleted and the bot confirms.
- **Given** I tap "Batal", **then** nothing is deleted.
- **Given** no records exist, **then** the bot replies that there is nothing to delete.

### FR-07 Unknown input ✅
- **Given** I send text outside any flow, or an unknown command, **then** the bot replies with a short hint to use `/help`.

---

## 8b. R2: Real tracker

Goal: know where my money is (every account) and how each pay cycle went, starting 27 October 2026.

### Business rules (R2)

| ID | Rule |
|---|---|
| BR-12 | **Accounts.** Every place money sits is an account: banks (CIMB, SeaBank), e-wallets (GoPay, OVO), Cash. Names are unique, ignoring case, 1 to 30 characters. |
| BR-13 | **Starting balance.** An account is added with its current real balance (0 or more, at most Rp10.000.000.000). Balances are typed by me, never synced from a bank. |
| BR-14 | **Balance.** Balance = starting balance + income − spending − transfers out + transfers in. |
| BR-15 | **Transfers are not spending.** Moving money between my accounts (top-up, cash withdrawal) changes balances but never counts as spending or income. |
| BR-16 | **Pay cycle.** A month runs from payday (`PAYDAY_DAY`, mine is the 27th) to the day before the next payday. If payday is past the end of a month, the cycle starts on that month's last day. |
| BR-17 | **Budget.** One budget per category, per pay cycle. Spending at 80% shows ⚠️, over 100% shows 🚨. |

### FR-08 Accounts `/akun`, `/saldo` ✅
- **Given** I send `/akun`, **then** the bot asks the name, then the current balance, and saves the account.
- **Given** the name already exists (any case), **then** the bot asks for another name.
- **Given** I send `/saldo`, **then** the bot lists each account's balance and the total.

### FR-09 Spending with account `/catat` ✅
- After the category, the bot shows account buttons (most recently used first); a forged or unknown account is rejected.
- The reply shows the account: `✅ nasi padang (Makan, GoPay) Rp25.000`.
- **Given** a budget exists for that category, **then** the reply also shows the budget bar for this cycle.
- **Given** there are no accounts, **then** the bot asks me to add one with `/akun`.

### FR-10 Income `/masuk` ✅
- Item → account → amount → `✅ Masuk: Gaji Oktober → CIMB Rp6.000.000`.

### FR-11 Transfer `/pindah` ✅
- From account → to account (the source is not offered) → amount → `✅ Pindah: CIMB → GoPay Rp200.000`.
- Needs at least 2 accounts. Same-account transfers are rejected, also from forged button data.

### FR-12 Pay cycle report `/bulan` ✅
- Shows the current cycle: income, spending, difference, spending per category (biggest first), budgets, and the change vs the previous cycle.
- ◀ / ▶ buttons move between cycles. There is no ▶ on the current cycle, and future or invalid button data is ignored.

### FR-13 Budgets `/budget` ✅
- `/budget Makan 1500000` sets or updates, `/budget Makan 0` removes, `/budget` lists all with bars.
- Unknown category or invalid amount: the bot explains the format.

### FR-14 Undo covers every kind ✅
- `/hapus` shows and deletes the newest transaction of any kind (spending, income, or transfer).

---

## 8c. R2.5: Keep the numbers right

### Business rules (R2.5)

| ID | Rule |
|---|---|
| BR-18 | **Every movement has a from and a to.** Money leaves `from_account` and enters `to_account` (either can be empty). Balance = starting balance + Σ in − Σ out, for every kind. |
| BR-19 | **Adjustment.** `/sesuaikan` records the difference between Prolog and the real app as an adjustment. It changes the balance but is never spending or income. |
| BR-20 | **Debts.** Lend, collect, borrow, repay are tracked per person (names unique, ignoring case). They change balances but are never spending or income. Paying back more than is owed is rejected. |
| BR-21 | **Subscriptions.** A recurring payment has a name, amount, category, account and due day (1 to 31; 31 means the last day in shorter months). On or after the due day the bot reminds once per month; nothing is logged until I confirm. A subscription added after this month's due day starts reminding next month. |
| BR-22 | **Edits.** Spending: name, amount, category, account. Income: name, amount, account. Transfers and debts: amount. Adjustments: delete only. |

### FR-15 History and edit `/riwayat` ✅
- Shows 8 entries per page, newest first, with ◀ ▶.
- Tapping an entry shows its detail and the edits allowed for its kind (BR-22), plus Hapus with confirmation.
- Forged button data (unknown id, field not allowed, unknown category or account) changes nothing.

### FR-16 Balance adjustment `/sesuaikan` ✅
- Pick an account → the bot shows Prolog's balance → I type the real balance → the difference is recorded, or "sudah sama" if equal.

### FR-17 Debts `/hutang` ✅
- Shows who owes whom, then 4 choices: Aku pinjamkan / talangi, Dia bayar ke aku, Aku pinjam, Aku bayar hutang.
- Paying back offers only people with an open balance in that direction and shows what's left. A fully paid debt says "Lunas" and leaves the list.

### FR-18 Subscriptions `/langganan` ✅
- Lists subscriptions with the monthly total; ➕ Tambah (name → category → account → amount → day) and 🗑 per item.
- The reminder has: ✅ Sudah bayar (logs the usual amount), ✏️ Jumlahnya beda (asks the amount), Lewati bulan ini.
- Tapping ✅ twice, or on a deleted subscription, logs nothing. A future month is rejected.

---

## 9. Non-functional requirements

| Area | Requirement |
|---|---|
| Security | Parameterized SQL only (`?` placeholders). All user input, including button data, is untrusted. Token only in `.env`, never printed or logged. |
| Speed | The bot replies within 2 seconds on a normal connection. |
| Reliability | A network error at startup shows a clear message. Data written before a crash is not lost (commit after each insert). |
| Data | PostgreSQL (SQLite until 26 Oct 2026). Schema changes use safe migrations that can run more than once. |
| Backup | Before R6 (server deploy), I copy `prolog.db` to a backup location at least weekly. |
| Testability | Validation and formatting logic live in plain functions that can be unit-tested without Telegram. |
| Learning | Build first, then understand every line by reading it back (reverse engineering). Claude explains on request (see `CLAUDE.md`). |

---

## 10. Data model (current)

```
accounts                                 budgets
├── id               INTEGER  PK         ├── category  TEXT     PK
├── name             TEXT     unique,    └── amount    INTEGER  > 0, per pay cycle
│                             no case
├── opening_balance  INTEGER  >= 0
└── created_at       TEXT

transactions
├── id             INTEGER  PK
├── kind           TEXT     'expense' | 'income' | 'transfer'
├── item           TEXT     not null
├── amount         INTEGER  > 0
├── category       TEXT     expenses only
├── account_id     INTEGER  → accounts (money leaves, or enters for income)
├── to_account_id  INTEGER  → accounts (transfers only)
└── created_at     TEXT     ISO 8601 with +07:00, the time I sent the command
```

No `user_id` column, because Prolog has a single owner (BR-01).

---

## 11. Release plan

| Release | Content |
|---|---|
| **R1 Money core** ✅ (v0.1.0, 26 Oct 2026) | FR-01 to FR-07: `/catat`, totals, `/hapus`, owner only, tests |
| **R2 Real tracker** ✅ code (target 1 Nov 2026) | FR-08 to FR-14: accounts, income, transfers, balances, pay cycles, budgets |
| **R2.5 Keep the numbers right** ✅ code | FR-15 to FR-18: history and edit, balance adjustment, hutang/piutang, subscriptions |
| R3 Android app | Native Android app with charts and fast input (cycle vs cycle, categories, balances, budgets). Needs an API on a server, so it includes the deploy and daily backups. The bot stays. Kotlin + Jetpack Compose. |
| R4 Targets and habits | Savings goals, daily 21:00 reminder if nothing was logged, automatic recap on payday |
| R5 Fast input | Natural typing (`nasi padang 25rb`), receipt photo reading with a "Benar?" check |
| R6 Bills and reminders | Recurring bills (PLN token, rent, tuition), reminders before due dates, timesheet reminder by the 1st |
| R7+ Modules | Reading log, Fitness log, Daily journal, People log, Ibadah check-in, Weekly recap |

### Module notes (future)
- **Reading log:** book + page + exact quote (typed, photo, or voice) + my own one-line meaning. No AI summaries. A daily old note is sent back to me (spaced repetition).
- **Weekly recap:** every Sunday, one message combining all modules ("this week: Rp X spent, 3 book notes, 4 workouts").

---

## 12. Success metrics

| Metric | Target |
|---|---|
| Logging habit | I log expenses on at least 5 days per week, for 4 weeks in a row |
| Speed | One expense takes under 15 seconds to log |
| Understanding | I can explain every function in `bot.py` without looking at notes |
| Shipping | R1 acceptance criteria all ✅ |
| Content | At least one Prorate video about building Prolog |

---

## 13. Open decisions

| Topic | Options | Status |
|---|---|---|
| One-line quick entry (`makan 25000`) | Bring back as a fast path next to `/catat`, or drop it | **Dropped** (25 Oct 2026): `/catat` is enough |
| R1 target date | To be set by me | **31 October 2026** |
| Transfer fees | Track admin fees on transfers, or not | **Not tracked** (26 Oct 2026): too much effort per entry; `/sesuaikan` fixes the drift |
| R3 face | Telegram Mini App, PWA, or native Android | **Native Android with Kotlin + Jetpack Compose** (26 Oct 2026). Tired of JS/TS, already tried Flutter, and native Android is a skill worth having |
| Hosting (now part of R3) | VPS, cloud free tier, or a home machine | Open: use the MacBook until I know I log daily |
| Track e-wallets and cash as accounts | Banks only, or every place money sits | **Every place** (26 Oct 2026): top-ups are transfers, so each balance matches its real app |
| Month = calendar or pay cycle | 1st to end of month, or payday to payday | **Pay cycle from the 27th** (26 Oct 2026) |
| Backup location | External drive, cloud storage, or private repo for backups | Open |

---

## 14. Glossary

| Term | Meaning |
|---|---|
| Module | One area of life Prolog logs (Money, Reading, Fitness, ...) |
| Flow | A multi-step conversation with the bot, like `/catat` |
| Owner | The single allowed user (me) |
| Polling | The bot asks Telegram for new messages (used now) |
| Webhook | Telegram sends messages to the bot's URL (used when deployed) |
