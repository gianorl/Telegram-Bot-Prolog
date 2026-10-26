# R1-01 Refactor: split bot.py into modules (no behavior change)

**Refs:** TECH_DESIGN §3, §6

## Goal
Move code into the target structure so it's testable and ready for new features. The bot must behave exactly the same after this.

## Tasks
- [x] Create `app/` package with `config.py`, `db.py`, `validators.py`, `formatters.py`, `handlers/money.py`
- [x] Move `rupiah()` to `formatters.py`
- [x] Move all SQL into `db.py` functions (`add_expense`, `total`, `total_by_category`)
- [x] `bot.py` only builds the app, registers handlers, and runs
- [x] Add `requirements.txt` (pinned versions) and `.env.example`

## Acceptance criteria
- [x] `/catat`, `/batal`, `/total`, `/total_by_category` work exactly as before
- [x] No SQL outside `db.py`
- [x] `ruff check .` passes
