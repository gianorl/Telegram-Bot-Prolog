# R1-10 Unit tests with pytest

**Refs:** TECH_DESIGN §10

## Tasks
- [x] `tests/test_validators.py`: every BR-02 to BR-05 case (valid, boundary, invalid)
- [x] `tests/test_formatters.py`: `rupiah(0)`, `rupiah(25000)`, `rupiah(1000000)`
- [x] `tests/test_db.py`: in-memory DB, migrations, totals on empty and filled tables, delete
- [x] `docs/MANUAL_TEST.md`: checklist of Telegram flows from the PRD acceptance criteria

## Acceptance criteria
- [x] `pytest` passes
- [x] Every PRD acceptance criterion is covered by a test or a manual checklist line
