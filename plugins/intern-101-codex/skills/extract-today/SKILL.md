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
3. For each selected session run `prepare --session "<id>" --offset 0`.
   Read every page using `next_offset` until it is null. If the fingerprint
   changes between pages, restart that session from offset 0. Do not skip pages
   or write the returned JSON to a file.
4. Follow [synthesis guidance](../../references/synthesis.md) directly in Codex.
   Feed each synthesis to `save` on standard input and save sequentially. If
   `save` reports that the session changed, reread and resynthesize it. The
   workflow does not require subagents.
5. Report saved paths, skipped unchanged sessions, and any failures.
