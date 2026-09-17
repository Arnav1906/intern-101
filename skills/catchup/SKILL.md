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

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/catchup.py" 2>&1
```

- `NONE` or no output → tell user: "No session history found. Run `/extract-today` first." Stop.
- First line is `STALE:<n>` → today's sessions exist but aren't in INDEX.md yet. Tell the user: "Found <n> session(s) from today not yet extracted — want me to run `/extract-today` first, or continue with what's indexed?" Wait for answer before proceeding. The remaining lines are the session list regardless of their choice.
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

Which to resume? Load:
  a) Summary only (recommended)
  b) Summary + sub-project progress
  c) Full detail (summary + transcript)
```

**Wait for answer before reading any file.**

## Step 3 — Load what was chosen

**Option a — Summary only:**
Read chosen `chat-contexts/<filename>`. Extract and present only `## Summary`, `## Key Decisions & Findings`, and `## Next Steps`. Do not surface the full file in context.

**Option b — Summary + progress:**
Read summary sections as above. Then check `projects/` for sub-project name matching session tags. Ask:
> "Also load `projects/<name>/_progress.md`?"
Wait for confirmation.

**Option c — Full detail:**
Read full chat-context file. Ask about `_progress.md` as above.

## Step 4 — Deliver briefing

```
## Resuming: <date> — <Title>

**What you were doing:**
<2-3 sentences from Summary>

**Where you left off:**
<`## Next Steps` from the context file if present; else pending items from _progress.md if loaded; else last 2-3 assistant turns>

**Immediate next step:**
<Single most actionable next thing>
```

Then ask: *"Want to pick up from here, or is there something new?"*
