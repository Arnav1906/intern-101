---
name: chat-context-extractor
description: Extract a selected Codex session or rollout path into a structured project context note; defaults to the latest project session.
---

Read [runtime guidance](../../references/runtime.md).

Use `prepare --session "<id>"` for a session ID or `prepare --path "<rollout>"`
for an explicit JSONL path. Without a selection, list `sessions` and choose the
latest entry. `--include-archived` is available for an explicitly requested
archived session.

Prepare the selected session with `--output ".intern101/prepared/<id>.json"`.
Read that snapshot and follow [synthesis guidance](../../references/synthesis.md).
Report the saved file path. If the session belongs to another project, explain
the mismatch and use the intended project explicitly only when requested.
