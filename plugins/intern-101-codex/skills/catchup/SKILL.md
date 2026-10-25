---
name: catchup
description: Use when the user starts a session and wants to know what they were working on, says "what was I doing yesterday", "let's start with what we left off", or types /catchup.
user_invocable: true
origin: intern-101
allowed-tools: [Read, Bash]
model: haiku
---

# /catchup — Resume From Last Session

## Step 1 — Scan INDEX.md only (no other files yet)

Resolve `<plugin-root>` from the loaded skill path as described in the [runtime reference](../../references/runtime.md).

```bash
python "<plugin-root>/scripts/catchup.py" 2>&1
```

- `NONE` or no output → tell user: "No extracted sessions found for this project." Stop.
- Lines returned → proceed to Step 2.

## Step 2 — Present menu, ask what to load

Show last sessions as a numbered list, including the summary column from each line:

```
Last sessions (up to 5):
  1. <date> — <title>
     <summary>
  2. <date> — <title>
     <summary>
  3. <date> — <title>  ← most recent
     <summary>

Which session would you like to resume? Load:
  a) Summary only (recommended)
  b) Summary + sub-project progress
```

**Wait for answer before reading any file.**

## Step 3 — Load what was chosen

**Option a — Summary only:**
Read chosen `chat-contexts/<filename>`. Extract and present only `## Summary`, `## Key Decisions & Findings`, and `## Next Steps`. Do not surface the full file in context.

**Option b — Summary + progress:**
Read summary sections as above. Then check `projects/` for sub-project progress matching the session tags and load it. If multiple projects match, ask which one. If none match, say no matching progress file was found.

## Step 4 — Deliver briefing

```
## Resuming: <date> — <Title>

**What you were doing:**
<2-3 sentences from Summary>

**Where you left off:**
<`## Next Steps` from the context file if present; else pending items from _progress.md if loaded; else say no next step was recorded>

**Immediate next step:**
<Single most actionable next thing, or "No next step recorded" if absent>
```

Then ask: *"Want to pick up from here, or is there something new?"*
