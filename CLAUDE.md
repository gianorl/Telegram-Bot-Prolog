# Prolog: Claude Code context

## What this is
Prolog ("Pro" + "log") is my personal life-logging Telegram bot. One umbrella app, many small modules, built one at a time. It is my first app of my own after four years as a developer. I want to understand every line, and document the journey as content (my TikTok series "Prorate: Programmer Rada Telat").

## Product spec
- `docs/PRD.md`: vision, scope, business rules, acceptance criteria, release plan (the "what").
- `docs/TECH_DESIGN.md`: architecture, structure, data, decisions (the "how").
- `docs/issues/`: R1 tasks in build order.
Read them before planning any feature, and check work against the acceptance criteria and business rules.

## How to work with me (IMPORTANT)
Mode since 25 Oct 2026: **build first, learn by reverse engineering.** I need the money tracker usable by end of October 2026.
- Claude writes the code to ship features fast, following the PRD, TECH_DESIGN and security rules.
- After each piece, give a short summary of what changed and where, so I can read it myself.
- I ask when I don't understand something; then switch to tutor style for that question (explain, analogies, quiz me on the reasoning).
- Keep code readable for a learner: small functions, clear names, short comments on the non-obvious parts.
- Be straightforward and fast: code first, short explanations, no long prose.
- Use simple ASCII diagrams and analogies (hiking, warung, ojol, basketball, books).
- Welcome my side questions. For design choices, give the strongest case for each side.
- Start each session with 1 or 2 review questions from "Review questions" below.
- Flag uncertainty. Read the actual code before claiming what it does.
- Don't remind me to commit or push. I know Git.
- Never print or log the bot token.

## Stack and setup (MacBook)
- Python 3.13, venv in `venv/` (activate: `source venv/bin/activate`, check for "(venv)")
- Libraries: python-telegram-bot (v22), python-dotenv, psycopg 3 + psycopg-pool
- Token in `.env` as `TELEGRAM_TOKEN` (never commit `.env`)
- Database: PostgreSQL 18 (Homebrew, `brew services start postgresql@18`), database `prolog` = my real data, `prolog_test` = wiped by tests. `DATABASE_URL` in `.env`. Old SQLite `prolog.db` and `backups/` are R1/R2 history, never commit
- Run: `python bot.py`, stop with Ctrl + C. Polling mode for now.
- Repo: github.com/gianorl/Telegram-Bot-Prolog (push via SSH)
- If startup fails with TimedOut / ConnectTimeout at get_me: network issue, not code.

## Security rules
- Parameterized SQL only (`%s` placeholders in psycopg). Never f-strings or string concat of values in SQL.
- Postgres never listens on the public internet; remote access (DBeaver, VPS) only through an SSH tunnel.
- Treat all user input as untrusted, including button `callback_data`.
- Secrets only in `.env`.

## Module 1: Money Tracker (current)
- v1: one-line input `makan 25000` -> parsed with `rsplit(" ", 1)` + `isdigit()`, saved to SQLite table `expenses (id, item, amount, created_at, category)`; `/total` shows sum and count
- v1.5: `/catat` guided flow with ConversationHandler: item -> category buttons (Makan, Transport, Belanja, Lainnya) -> amount; `/batal` cancels
- v2: receipt photo saved with the entry as proof
- v3: bot reads the receipt photo (amount, store, date) and asks "Benar?" with buttons
- v4: `/bulan` total by category this month
- v5: bills and reminders (PLN token, rent, tuition, timesheet by the 1st)

## Current status (R2.5)
R1 done (v0.1.0). R2 + R2.5 code written 26 Oct 2026: accounts, `/masuk`, `/pindah`, pay cycles from the 27th, `/bulan`, `/budget`, `/riwayat` (edit/delete any entry), `/sesuaikan`, `/hutang`, `/langganan` with reminders. Switched to PostgreSQL 26 Oct 2026 (fresh schema; `schema_version` 2 = categories table). Backups of the old SQLite file in `backups/`.
Decided: track every place money sits (banks, e-wallets, cash); no transfer fees; R3 = native Android app.
Deployed 26 Oct 2026 to a Tencent Lighthouse VPS (Jakarta), see `docs/SERVER.md`. **The server DB is the real data; never run the bot on the Mac again** (two polling bots fight). Deploy with `./scripts/deploy.sh`.
Next: nightly backups, DBeaver over SSH tunnel, run `docs/MANUAL_TEST.md`. Then R3: API, Android app (Kotlin + Compose).

## Later modules (planned)
- Reading log: book + page + exact quote (typed, photo, or voice) + my own one line; daily review note (spaced repetition). No AI summaries.
- Fitness log, daily one-line journal, weekly recap, people log, ibadah check-in
- R3 "face": native Android app in **Kotlin + Jetpack Compose** (decided 26 Oct 2026) talking to an API on a server; the bot stays for quick input. Kotlin is new to me: explain with Kotlin ↔ TypeScript comparisons when I ask.

## Review questions (spaced repetition)
- Why activate the venv before pip install?
- Why is `venv/` in .gitignore? Why `prolog.db`?
- What does `await` do, and why does the bot need it?
- What does `~filters.COMMAND` mean?
- Why `rsplit` at the LAST space instead of `split`?
- Why must the ConversationHandler be added before the one-line MessageHandler?
- Why use `?` placeholders instead of f-strings in SQL?
