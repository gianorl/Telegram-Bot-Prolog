# R1-06 Conversation timeout and WIB timestamps

**Refs:** PRD BR-07, BR-09 · TECH_DESIGN §6, §7

## Tasks
- [x] Install `python-telegram-bot[job-queue]`, update `requirements.txt`
- [x] `ConversationHandler(conversation_timeout=300)`, clear `user_data` on timeout
- [x] Save `created_at` with `datetime.now(ZoneInfo("Asia/Jakarta")).isoformat()`

## Acceptance criteria
- [x] Given I start `/catat` and don't reply for 5 minutes, then nothing is saved and the next message is not treated as part of the old flow
- [x] New records have `+07:00` in `created_at`
