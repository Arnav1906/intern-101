---
name: catchup
description: Use when the user starts a session and wants to know what they were working on, says "what was I doing yesterday", "let's start with what we left off", or types /catchup. Presents last sessions as a menu and asks what to load before reading anything.
user_invocable: true
---

# /catchup — Resume From Last Session

## Step 1 — Scan INDEX.md only (no other files yet)

```bash
python -c "
import os, re

idx_path = os.path.join(os.getcwd(), 'chat-contexts', 'INDEX.md')
if not os.path.isfile(idx_path):
    print('NONE')
else:
    rows = [l for l in open(idx_path, encoding='utf-8').readlines()
            if l.strip().startswith('|') and '---' not in l and 'Date' not in l and l.strip() != '|']
    for r in rows[-3:]:
        m = re.search(r'\`([^`]+\.md)\`', r)
        title = re.findall(r'\|([^|]+)', r)
        date = title[1].strip() if len(title) > 1 else ''
        t = title[2].strip() if len(title) > 2 else ''
        fname = m.group(1) if m else ''
        if fname: print(date + ' | ' + t + ' | ' + fname)
" 2>&1
```

- `NONE` or no output → tell user: "No session history found. Run `/extract-today` first." Stop.
- Lines returned → proceed to Step 2.

## Step 2 — Present menu, ask what to load

Show last sessions as a numbered list:

```
Last sessions:
  1. <date> — <title>
  2. <date> — <title>
  3. <date> — <title>  ← most recent

Which to resume? Load:
  a) Summary only (recommended)
  b) Summary + sub-project progress
  c) Full detail (summary + transcript)
```

**Wait for answer before reading any file.**

## Step 3 — Load what was chosen

**Option a — Summary only:**
Read chosen `chat-contexts/<filename>`. Extract and present only `## Summary` and `## Key Decisions & Findings`. Do not surface the full file in context.

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
<Pending items from _progress.md if loaded, else last 2-3 assistant turns>

**Immediate next step:**
<Single most actionable next thing>
```

Then ask: *"Want to pick up from here, or is there something new?"*

## Notes

- Never bulk-read files without asking first.
- Do not read raw `.jsonl` files — only extracted `chat-contexts/` markdown files.
- If `chat-contexts/` doesn't exist: "No session history yet. Run `/extract-today` after your first session."
