# R1-02 FR-01 Owner-only access

**Refs:** PRD BR-01, FR-01 · TECH_DESIGN §4, §5

## Tasks
- [x] Add `OWNER_ID` to `.env` and `.env.example`
- [x] `config.py` fails fast if `OWNER_ID` is missing or not an integer
- [x] `auth.py`: `owner_guard` raises `ApplicationHandlerStop` for non-owners
- [x] Register with `TypeHandler(Update, owner_guard)` in group -1

## Acceptance criteria
- [x] Given a non-owner sends any message, command, or button tap, then the bot does not reply and nothing is saved
- [x] Given I am the owner, then all commands work
- [x] Given `OWNER_ID` is missing, then the bot exits at startup with a clear message

## How to test
Ask a friend to message the bot, or use a second Telegram account.
