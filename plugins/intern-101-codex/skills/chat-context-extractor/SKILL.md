---
name: chat-context-extractor
description: Extract a selected Codex session or rollout path into a structured project context note; defaults to the latest project session.
---

Read [runtime guidance](../../references/runtime.md).

Use `prepare --session "<id>"` for a session ID or `prepare --path "<rollout>"`
for an explicit JSONL path. Without a selection, list `sessions` and choose the
latest entry. `--include-archived` is available for an explicitly requested
archived session.

Read the selected session with `prepare --offset 0`, then continue with each
`next_offset` until it is null. Keep the selection and fingerprint consistent
across pages; restart if the session changes. Do not write the returned JSON to
a file. Follow [synthesis guidance](../../references/synthesis.md), feeding the
synthesis to `save` on standard input. If `save` reports a changed session,
reread and resynthesize it.
Report the saved file path. If the session belongs to another project, explain
the mismatch and use the intended project explicitly only when requested.
