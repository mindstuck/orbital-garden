# ADR 0003: Wake word and activation state

- Status: proposed
- Date: 2026-10-09

## Context

Wake-word activation is a next-stage feature. The current client uses
push-to-talk only. Introducing wake word must not move audio decisions into
the server coordinator or weaken the existing access boundary.

## Decision

- Wake-word detection stays at the **audio/client boundary** (the browser or a
  small local detector). The server only sees explicit `audio_start` /
  `audio_end` events and never guesses activation.
- The client exposes an explicit activation state machine:
  - `idle` — not listening, no capture.
  - `listening` — capture running, waiting for end of speech or cancel.
  - `active` — a turn is in progress.
- **Push-to-talk remains the fallback** and transitions directly to
  `listening`/`active`, bypassing wake word.
- Activation is **not authorization**: the origin/access check on `/ws`
  continues to apply regardless of how a turn was started.
- Wake-word accuracy/CPU cost is measured on target hardware before the state
  machine is enabled by default.

## Consequences

- No server changes are required to add wake word.
- `web/app.js` keeps capture logic in one place so the state machine can be
  added without touching the coordinator or protocol.
- Until implemented, the default remains push-to-talk.
