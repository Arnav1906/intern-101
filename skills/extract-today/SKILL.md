---
name: extract-today
description: Use when the user wants to save all of today's Claude sessions as context documents, says "extract today's sessions", or types /extract-today.
user_invocable: true
origin: intern-101
model: sonnet
allowed-tools: [Read, Write, Bash]
---

# /extract-today — Batch Extract All New Sessions for Today

## Step 1 — Find today's new sessions

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/extract_today.py" 2>&1
```

Parse the output as JSON.

- `ERROR:` → report and stop.
- `[]` → "No new sessions found for today. All `.jsonl` files are already extracted or none exist." Stop.

## Step 2 — Present list and ask for confirmation

```
Found N new session(s) from today:

  #  Time   Size    UUID
  1  09:14  42 KB   f4fa97f5-...
  2  11:30  18 KB   9d5fbcf9-...

Extract all? Or enter numbers to skip (e.g. "skip 2"):
```

**Wait for answer before proceeding.**

- "yes" / "all" / enter → process all
- "skip N" → remove N and process rest
- "no" / "cancel" → stop

Flag any session under 5 KB: "Session #N is very small (X KB). Include anyway?"

## Step 3 — Phase 1: Parse each confirmed session

For each confirmed session, run:

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/chat_context_extractor.py" "<jsonl_path>" 2>&1
```

Parse the last non-empty line of stdout as JSON.
If a session returns `ERROR:` → report it and skip.

You now have one JSON object per session with this schema:
```json
{
  "session_id": "str",
  "custom_title": "str",
  "model": "str",
  "date": "YYYY-MM-DD",
  "first_ts": "str",
  "last_ts": "str",
  "turns": [
    {"role": "user",      "hhmm": "HH:MM", "text": "str"},
    {"role": "assistant", "hhmm": "HH:MM", "text": "str", "tools": ["str"]}
  ],
  "files_modified": ["str"],
  "session_count": 1,
  "project_root": "str",
  "total_user": 0,
  "total_assistant": 0
}
```

Verify `turns` is non-empty; if not, report and skip that session.

## Step 4 — Phase 2: Dispatch synthesis agents

Spawn one **`intern-101:chat-context-extractor`** sub-agent **per session simultaneously** (do not wait for one to finish before spawning the next).

For each session, pass the full lean JSON from Step 3 as the agent's prompt, prefixed with:

> Synthesize a context document from this cleaned session JSON and write it to disk. JSON: `<paste full JSON here>`

Wait for all agents to complete. Each agent writes its own `.md` file and updates INDEX.md — no manual file writing needed.

## Step 5 — Summary

Collect the confirmation blocks returned by each agent. Report:

```
Extracted N session(s) for <today>:
  <confirmation block from agent 1>
  <confirmation block from agent 2>

INDEX.md updated.
```

## Notes

- Sessions matched as "new" by UUID not appearing in existing frontmatter `session_id` fields.
- Files < 5 KB are likely metadata-only — flag: "Session #N is very small (X KB). Include anyway?"
- Only processes today's files. For older sessions, use `chat-context-extractor` directly with a path.
