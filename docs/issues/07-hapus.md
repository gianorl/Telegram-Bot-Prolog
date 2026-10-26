# R1-07 FR-06 /hapus undo last entry

**Refs:** PRD BR-08, FR-06

## Tasks
- [x] `db.py`: `last_expense()`, `delete_expense(id)`
- [x] `/hapus` shows the last record with buttons "Ya, hapus" and "Batal"
- [x] Button data includes the record id; validate it before deleting

## Acceptance criteria
- [x] Given records exist, `/hapus` shows the newest one with two buttons
- [x] "Ya, hapus" deletes it and confirms
- [x] "Batal" deletes nothing
- [x] Given no records, the bot says there is nothing to delete
