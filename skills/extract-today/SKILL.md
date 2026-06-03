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
  "title": "...",
  "files_modified": [...],
  "tags": "...",
  "transcript": "..."
}
```

## Step 4 — Phase 2: Spawn parallel sub-agents

Spawn one sub-agent **per session simultaneously** (do not wait for one to finish before spawning the next). Each sub-agent receives this prompt, with `{title}`, `{files_modified}`, and `{transcript}` filled in from the Phase 1 JSON:

```
You are summarizing a Claude Code work session for an intern's session log.

Session title: {title}
Files modified: {files_modified}

Transcript:
{transcript}

Write:
1. ## Summary — 2-3 sentences describing what was worked on and what was accomplished.
2. ## Key Decisions & Findings — 3-8 bullet points of concrete decisions, findings, or changes made.
3. One-liner — a single sentence (max 120 chars) for the session index.

Return ONLY valid JSON, no other text:
{
  "summary": "2-3 sentence paragraph.",
  "decisions": ["- Decision or finding one.", "- Decision or finding two."],
  "one_liner": "Single sentence under 120 chars."
}
```

Wait for all sub-agents to complete before proceeding.

## Step 5 — Write files (sequential, chronological order)

For each completed session:

**1. Compute the output filename:**
`{date}_{slug}.md` where slug = title lowercased, spaces replaced with hyphens, non-alphanumeric characters removed, max 50 chars.

**2. Write the `.md` file to `chat-contexts/`:**

```
---
session_id: {session_id}
date: {date}
---

# {title}
**Date:** {date}  **Session:** {session_id}

## Summary
{summary from sub-agent}

## Key Decisions & Findings
{decisions from sub-agent, one per line}

## Files Modified
{files_modified as bullet list, or "- None recorded." if empty}

## Tags
{tags}
```

**3. Update INDEX.md:**

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/update_index.py" \
  --date "{date}" \
  --title "{title}" \
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
