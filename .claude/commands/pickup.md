---
description: Resume work from the last /handoff
---

1. Read `.claude/handoff/NEXT.md`. If it doesn't exist, say so and stop.
2. Check that the branch and last commit it names match `git status` and `git log -1`. If they don't, tell me what changed before doing anything else.
3. Read the files under "Read first".
4. Give me a five-line summary: goal, state, and the next three steps.
5. Start the first unchecked step:
   - `[sonnet]` steps: delegate to the `mechanical` agent.
   - `[opus]` steps: do them yourself if this session is on Opus; otherwise delegate to the `deep` agent.
   - Use the `scout` agent for any lookup in large files.
6. Tick each step off in `NEXT.md` as it is finished, and stop to ask me at any step tagged as waiting on me.

$ARGUMENTS
