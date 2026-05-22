---
name: recall
description: Use when the user wants to find past sessions related to a topic, asks "did we work on X before?", "find sessions about Y", or types /recall <query>.
user_invocable: true
origin: intern-101
allowed-tools: [Read, Bash]
---

# /recall — Find Past Sessions

## Step 1 — Show 5 most recent sessions (always)

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/recall.py" 2>&1
```

- `NONE` → "No session history yet. Run `/extract-today` first." Stop.
- Lines returned → display as numbered list:

```
Recent sessions:
  1. YYYY-MM-DD — <Title>
  2. YYYY-MM-DD — <Title>
  ...
```

If `{{ arguments }}` is non-empty, proceed to Step 2 (search). Otherwise ask: "Open one (enter number), or type a search term."

**Wait for answer.** If user enters a number → jump to Step 4. If user enters text → treat as query and run Step 2.

## Step 2 — Search INDEX.md titles

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/recall.py" --query "{{ arguments }}" 2>&1
```

- `NONE` → "No title matches for '{{ arguments }}'. Want me to search inside file contents?"
- Matches → proceed to Step 3.

## Step 3 — Present search matches

Show matched rows as a numbered list (continuing from Step 1 numbering if helpful):

```
Found N session(s) matching "{{ arguments }}":

  1. YYYY-MM-DD — <Title>  [<filename>]
  2. YYYY-MM-DD — <Title>  [<filename>]
```

Ask: "Open one (enter number), or 'search content' to grep file bodies."

**Wait for answer.**

## Step 4 — Load chosen session or expand search

**If number entered:** Read that `chat-contexts/<filename>`, present `## Summary` and `## Key Decisions & Findings`. Offer to load full file.

**If "search content":**

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/recall.py" --query "{{ arguments }}" --content 2>&1
```

Show results numbered. Ask which to open.

## Notes

- Step 1 always runs — recent sessions shown even with no query.
- Only reads from `chat-contexts/` — never raw `.jsonl` files.
- Case-insensitive throughout.
