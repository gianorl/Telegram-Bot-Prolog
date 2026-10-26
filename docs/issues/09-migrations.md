# R1-09 Migrations with PRAGMA user_version

**Refs:** TECH_DESIGN §6, D6

## Tasks
- [x] Numbered migration list in `db.py`
- [x] On startup: read `PRAGMA user_version`, run newer migrations in order, set the new version
- [x] Remove the old `try / except ALTER TABLE`
- [x] Back up `prolog.db` before running this the first time

## Acceptance criteria
- [x] Existing data survives
- [x] Running the bot twice does not re-run migrations
- [x] A fresh database gets the full schema
