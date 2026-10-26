# R1-12 Decision: one-line quick entry (`makan 25000`)

**Refs:** PRD §13

## Question
Bring back one-line entry as a fast path next to `/catat`, or drop it?

## Options
- **Keep:** fastest logging (one message). Needs parsing rules and must not clash with the unknown-input hint (R1-08).
- **Drop:** simpler code. Every entry takes 3 to 4 messages.

## Done when
- [x] Decision recorded in PRD §13 and TECH_DESIGN §12

## Decision
**Dropped** (25 Oct 2026). `/catat` is enough.
