---
name: chat-context-extractor
description: Reads a Claude Code .jsonl session transcript and produces a structured, searchable markdown context document. When no path is given, auto-locates the most recent session from ~/.codex/sessions/ for the current working directory. Works on Windows, macOS, and Linux.
user_invocable: true
model: sonnet
---

# Chat Context Extractor

Processes a Claude Code `.jsonl` session into a condensed context document.

## Input

Path optionally provided via `{{ arguments }}`.

- **Path given:** use it directly.
- **No path:** run Step 0 to auto-locate the latest session.

---

## Step 0 — Auto-Locate Latest Session (only when no path given)

```bash
python "<plugin-root>/scripts/latest_session.py" 2>&1
```

Parse last non-empty line. If `ERROR:` → report and stop.

---

## Step 1 — Clean the Transcript

Run the cleaner (substitute the resolved path for `<path>`).

Resolve `<plugin-root>` from the loaded skill path as described in the [runtime reference](../../references/runtime.md).

```bash
python "<plugin-root>/scripts/chat_context_extractor.py" "<path>" 2>&1
```

Parse the last non-empty line of stdout as JSON.
If the line starts with `ERROR:` → report the error and stop.
If `turns` is empty → report "metadata-only or corrupted session" and stop.

---

## Step 2 — Dispatch Synthesis Agent

Read the packaged `agents/chat-context-extractor.md` and pass its instructions
to a Codex subagent together with the cleaned session JSON.

Pass the full JSON object from Step 1 as the agent's prompt, prefixed with:

> Synthesize a context document from this cleaned session JSON and write it to disk. JSON: `<paste full JSON here>`

Wait for the agent to return its confirmation block, then output it verbatim.

---

## Edge Cases

- Step 0 fails → report error, stop
- Step 1 produces `ERROR:` → report, stop
- Existing output file → agent appends `_v2`, `_v3` suffix
- Multiple session IDs in JSON → agent notes in Summary
