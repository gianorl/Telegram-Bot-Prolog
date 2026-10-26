# R1-08 FR-07 Unknown input hint

**Refs:** PRD FR-07

## Tasks
- [x] Add a low-priority handler (registered last) for text outside any flow and unknown commands

## Acceptance criteria
- [x] Given I send random text or `/xyz` outside a flow, the bot replies with a hint to use `/help`
- [x] The hint does NOT fire while I'm inside `/catat`
