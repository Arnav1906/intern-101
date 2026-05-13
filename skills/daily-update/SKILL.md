---
name: daily-update
description: Use when the user wants to generate a daily status update for their supervisor, says "write my daily update", "what did I do today", or types /daily-update. Auto-sources from today's chat-context files when no notes are provided, and rephrases technical jargon into plain language.
user_invocable: true
---

# /daily-update — Daily Status Update

Three modes:
- **`--yesterday`:** same as auto-mode but pulls yesterday's sessions.
- **No arguments:** auto-pulls today's session summaries from `chat-contexts/`.
- **Other arguments:** uses the provided notes directly (skip to Format Step).

---

## Manual Mode (arguments provided)

If `{{ arguments }}` is non-empty, skip to the **Format Step**.

---

## Auto Mode (no arguments)

### Step 1 — Find today's chat-context files

```bash
python -c "
import os, glob
from datetime import datetime, timedelta

arg = '{{ arguments }}'.strip().lower()
if arg == '--yesterday':
    target_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
else:
    target_date = datetime.now().strftime('%Y-%m-%d')
ctx_dir = os.path.join(os.getcwd(), 'chat-contexts')
if not os.path.isdir(ctx_dir):
    print('NONE')
else:
    results = [f for f in sorted(glob.glob(os.path.join(ctx_dir, '*.md')))
               if os.path.basename(f).startswith(target_date) and os.path.basename(f) != 'INDEX.md']
    print('\n'.join(results) if results else 'NONE')
" 2>&1
```

- `NONE` → tell user: "No chat-context files found for today. Run `/extract-today` first, or paste your notes directly." Stop.

### Step 2 — Ask before reading

Show files found and ask:

```
Found N session(s) from today:
  1. <date>_<slug1>.md
  2. <date>_<slug2>.md

Read these to generate your daily update? (yes / enter numbers to skip)
```

**Wait for confirmation.**

### Step 3 — Extract summaries only

For each confirmed file, extract only `## Summary`, `## Key Topics`, and `## Key Decisions & Findings` sections:

```bash
python -c "
import re, os

files = [r'FILE1', r'FILE2']
out = []
for f in files:
    txt = open(f, encoding='utf-8').read()
    m = re.search(r'^# (.+)$', txt, re.MULTILINE)
    out.append('=== ' + (m.group(1) if m else f) + ' ===')
    for sec in ['## Summary', '## Key Topics', '## Key Decisions & Findings']:
        m2 = re.search(re.escape(sec) + r'\n(.*?)(?=\n## |\Z)', txt, re.DOTALL)
        if m2: out.append(sec + '\n' + m2.group(1).strip())
    out.append('')
print('\n'.join(out))
" 2>&1
```

### Step 4 — Ask for name if unknown

If the user's name is not in context: "What name should appear on the update?"

---

## Format Step

Apply these rules to produce the final update:

### Simplification rules

**Rephrase these:**

| Technical form | Rephrase as |
|---|---|
| SP names (`SP_ADOPT_*`, `SP_CONFIGURE_*`) | What the script does: "the composite rate adoption script" |
| Table names (`CNF_*`, `LOG_*`, `SOL_*`, `PRD_*`) | What it holds: "the configuration table", "the release tracking log" |
| File names with extensions | Type + purpose: "the database script", "the automation tool" |
| Internal API/endpoint names | The action: "an API call to retrieve class codes" |
| Technical terms (XPath, COALESCE, WAR cache, jqGrid) | Plain English: "a display condition", "a fallback value", "the application cache" |
| DB operations (INSERT, UPDATE, SELECT-cum-INSERT) | "added a record", "updated an entry", "prepared and inserted data" |

**Keep as-is:**
Colleague names and initials, Postman/GitLab/Bugzilla, bug URLs, business domain terms (ERC adoption, ISO coverage, composite rates, rental reimbursement).

### Output format

```
[Name] Daily Update – DD/MM/YY

* [bullet]
* [bullet]
* [BLOCKER] [blocked/pending item]
```

- Exactly **5–7 bullets**. Merge related items; do not pad.
- Under 200 words total.
- No section headers, greetings, sign-offs, or commentary.
- Prefix blocked or pending items with `[BLOCKER]`.

---

## Notes

- Multiple sessions today → synthesise across all, still 5–7 bullets total.
- Thin content (very short sessions) → ask: "Activity today looks light. Anything to add?" before generating.
- Never read raw `.jsonl` files — only `chat-contexts/` markdown files.
