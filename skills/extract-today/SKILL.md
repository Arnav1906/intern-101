---
name: extract-today
description: Use when the user wants to save all of today's Claude sessions as context documents, says "extract today's sessions", or types /extract-today.
user_invocable: true
origin: intern-101
allowed-tools: [Read, Write, Bash]
---

# /extract-today — Batch Extract All New Sessions for Today

## Step 1 — Find today's new sessions

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/extract_today.py" 2>&1
```

Parse last non-empty line as JSON.

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
- "skip N" → remove and process rest
- "no" / "cancel" → stop

## Step 3 — Extract each confirmed session

For each confirmed session, run:

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/extract_today.py" --run "<jsonl_path>" 2>&1
```

Process one at a time, chronological order. After each:

```
✓ [HH:MM] Extracted → chat-contexts/<date>_<slug>.md
```

## Step 4 — Summary

```
Extracted N session(s) for <today>:
  chat-contexts/<date>_<slug1>.md
  chat-contexts/<date>_<slug2>.md

INDEX.md updated. Sub-project _Index.md files updated where matched.
```

## Notes

- Sessions matched as "new" by UUID not appearing in existing frontmatter `session_id` fields.
- Files < 5 KB are likely metadata-only — flag: "Session #N is very small (X KB). Include anyway?"
- Only processes today's files. For older sessions, use `chat-context-extractor` directly with a path.
