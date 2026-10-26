# R1-03 Logging and error handler

**Refs:** TECH_DESIGN §9

## Tasks
- [x] Configure `logging` at INFO
- [x] Set the `httpx` logger to WARNING (its INFO logs contain the token in URLs)
- [x] Add `app.add_error_handler(...)`: log the exception, reply with a short generic message

## Acceptance criteria
- [x] Running the bot never prints the token
- [x] A forced exception in a handler is logged and the user gets a short error reply
