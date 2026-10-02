---
name: extract-today
description: Save today's new or continued Codex sessions for the current project as structured Markdown context notes.
---

Read [runtime guidance](../../references/runtime.md).

1. Run `sessions --today --new`. Present session IDs, times, and previews. Report
   any errors separately; an unreadable session is not an already extracted one.
2. If the user already requested saving all today's sessions, proceed with those
   sessions. Otherwise ask which sessions to include. No matches means nothing
   new to save.
3. For each selected session run `prepare --session "<id>" --output
   ".intern101/prepared/<id>.json"`. Read the snapshot.
4. Follow [synthesis guidance](../../references/synthesis.md) directly in Codex.
   Save each synthesis sequentially. The workflow does not require subagents.
5. Report saved paths, skipped unchanged sessions, and any failures.
