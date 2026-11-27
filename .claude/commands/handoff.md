---
description: Save where this session got to, so the next session (on any model) can pick up cleanly
model: sonnet
---

Write (overwrite) `.claude/handoff/NEXT.md` so a fresh session can continue this work with no other context. Create the folder if needed. Keep it under 60 lines and use exactly these sections:

## Goal
One or two sentences: what we are trying to achieve and why.

## State
- Branch, last commit (short hash and subject), and any uncommitted files (`git status --short`).
- Anything running or waiting (a bench campaign, a CI run, an App Review reply, an upstream release).

## Done this session
Bullets: what was finished, with commit hashes or PR numbers.

## Next steps
A checklist in order. Tag each item `[sonnet]` if its steps are already known (docs, config, applying a decided plan, running tests) or `[opus]` if it still needs diagnosis or design. Be specific enough that the step can be done without asking.

## Decisions and open questions
What was decided (and why, briefly), and what is waiting on the user.

## Read first
The 3-6 files a new session should read before starting.

$ARGUMENTS

Do not commit `NEXT.md`. When done, reply with one line: where the file is and the first next step.
