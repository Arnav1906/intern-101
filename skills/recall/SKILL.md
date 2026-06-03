---
name: recall
description: Use when the user wants to find past sessions related to a topic, asks "did we work on X before?", "find sessions about Y", or types /recall <query>.
user_invocable: true
origin: intern-101
model: haiku
allowed-tools: [Read, Bash]
---

# /recall — Find Past Sessions

## Step 1 — Show all sessions

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/recall.py" 2>&1
```

- `NONE` → "No session history yet. Run `/extract-today` first." Stop.
- Lines returned → display as a numbered list, newest first:

```
All sessions (N):
  1. YYYY-MM-DD — <Title>
               <one-line summary>
  2. YYYY-MM-DD — <Title>
               <one-line summary>
  ...
```

If `{{ arguments }}` is non-empty, proceed directly to Step 2. Otherwise ask: "Open one (enter number), or type a search term."

**Wait for answer.** Number entered → Step 4. Text entered → Step 2.

## Step 2 — Search INDEX.md titles

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/recall.py" --query "{{ arguments }}" 2>&1
```

- `NONE` → "No title matches for '{{ arguments }}'. Want me to search inside file contents?"
- Matches → proceed to Step 3.

## Step 3 — Present search matches

```
Found N session(s) matching "{{ arguments }}":

  1. YYYY-MM-DD — <Title>  [<filename>]
               <one-line summary>
```

Ask: "Open one (enter number), or 'search content' to grep file bodies."

**Wait for answer.**

## Step 4 — Load chosen session or expand search

**If number entered:** Read `chat-contexts/<filename>`, present `## Summary` and `## Key Decisions & Findings`. Offer to load full file.

**If "search content":**

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/recall.py" --query "{{ arguments }}" --content 2>&1
```

Show results numbered. Ask which to open.

## Notes

- Always reads from `INDEX.md` — never raw `.jsonl` files.
- Case-insensitive throughout.
