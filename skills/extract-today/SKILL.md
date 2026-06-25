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

Collect the JSON output for each session. If a session returns `ERROR:`, report it and skip.

You now have one JSON object per session:
```json
{
  "session_id": "...",
  "date": "...",
  "title_hint": "...",
  "files_modified": [...],
  "tags": "...",
  "transcript": "...",
  "turn_count": 42
}
```

## Step 4 — Phase 2: Spawn parallel sub-agents

Spawn one sub-agent **per session simultaneously** (do not wait for one to finish before spawning the next). Each sub-agent receives this prompt, with `{title_hint}`, `{files_modified}`, `{turn_count}`, and `{transcript}` filled in from the Phase 1 JSON:

```
You are summarizing a Claude Code work session for an intern's session log.

Title hint (do NOT copy verbatim — use as context only): {title_hint}
Files modified: {files_modified}
Turn count: {turn_count}

Transcript:
{transcript}

Produce a structured summary. Return ONLY valid JSON, no other text:
{
  "title": "Concise descriptive title (max 80 chars) capturing the session's main theme and outcome — NOT just the first message",
  "what_worked_on": ["- bullet describing a topic or area worked on"],
  "what_accomplished": ["- bullet describing a concrete outcome, change, or result"],
  "key_decisions": ["- bullet describing a significant decision or finding"],
  "blockers_issues": ["- bullet for any blocker, bug, or unresolved issue (omit array if none)"],
  "next_steps": ["- bullet for follow-up actions mentioned or implied (omit array if none)"],
  "one_liner": "Single sentence under 120 chars summarising the session for an index."
}

Rules:
- what_worked_on: 2-5 bullets, describe WHAT areas/features/problems were touched
- what_accomplished: 2-6 bullets, describe concrete OUTPUTS (files written, bugs fixed, features working)
- key_decisions: 2-6 bullets, architecture choices, approach selections, trade-offs made
- blockers_issues: only include if genuinely present in transcript
- next_steps: only include if explicitly mentioned or clearly implied
- title: must be specific enough that reading it tomorrow tells you exactly what session this was
```

Wait for all sub-agents to complete before proceeding.

## Step 5 — Write files (sequential, chronological order)

For each completed session:

**1. Compute the output filename:**
`{date}_{slug}.md` where slug = `title` (from sub-agent) lowercased, spaces replaced with hyphens, non-alphanumeric characters removed, max 50 chars.

**2. Write the `.md` file to `chat-contexts/`:**

```
---
session_id: {session_id}
date: {date}
---

# {title from sub-agent}
**Date:** {date}  **Session:** {session_id}

## What Was Worked On
{what_worked_on from sub-agent, one bullet per line}

## What Was Accomplished
{what_accomplished from sub-agent, one bullet per line}

## Key Decisions
{key_decisions from sub-agent, one bullet per line}

## Blockers & Issues
{blockers_issues from sub-agent, one bullet per line — omit entire section if array is empty or absent}

## Next Steps
{next_steps from sub-agent, one bullet per line — omit entire section if array is empty or absent}

## Files Modified
{files_modified as bullet list, or "- None recorded." if empty}

## Tags
{tags}
```

**3. Update INDEX.md:**

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/update_index.py" \
  --date "{date}" \
  --title "{title from sub-agent}" \
  --filename "{output_filename}" \
  --summary "{one_liner from sub-agent}"
```

Confirm output starts with `INDEXED:`.

## Step 6 — Summary

```
Extracted N session(s) for <today>:
  chat-contexts/<filename1>
  chat-contexts/<filename2>

INDEX.md updated.
```

## Notes

- Sessions matched as "new" by UUID not appearing in existing frontmatter `session_id` fields.
- Files < 5 KB are likely metadata-only — flag: "Session #N is very small (X KB). Include anyway?"
- Only processes today's files. For older sessions, use `chat-context-extractor` directly with a path.
