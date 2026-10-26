# R1-05 FR-02 Validation rules as pure functions

**Refs:** PRD BR-02 to BR-05 · TECH_DESIGN §8

## Tasks
- [x] `validators.py`: `validate_item`, `parse_amount`, `validate_category` raising `ValueError` with a user-facing message
- [x] Handlers use them and reply with the error message on failure
- [x] Add max amount Rp100.000.000 and item length 1 to 100

## Acceptance criteria
- [x] Item over 100 chars is rejected, user stays on the item step
- [x] Amount `0`, negative, non-digit (`abc`, `25rb`, `25.000`), or over 100.000.000 is rejected, user stays on the amount step
- [x] Forged category is rejected
