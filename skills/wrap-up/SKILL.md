---
name: wrap-up
description: Use when the user says they are done for the day — "I'm done", "wrapping up", "done for today", "signing off", "that's it for today", "I'm finished", "end of day". Checks git status, prompts to commit if needed, then runs session extraction. Fully self-contained, no external skill dependencies.
origin: intern-101
user-invocable: true
allowed-tools: [Read, Bash]
---

# /wrap-up — End-of-Day Wrap-Up

Checks git status, optionally commits, then extracts today's sessions. Fully self-contained — no external skills or plugins.

---

## Step 1 — Git repo check

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/wrap_up.py" --check
```

Read the output:

- `NO_REPO` → skip to Step 3
- `CLEAN` → skip to Step 3
- Starts with `DIRTY:` → the rest of the line contains the branch name and changed file list. Proceed to Step 2.

---

## Step 2 — Uncommitted changes: ask user

Show the changed files from the `DIRTY:` output and present this exact choice:

```
You have uncommitted changes on branch `<branch>`:
<file list>

Commit before extracting today's sessions?
  y) Yes — commit now
  n) No  — skip and extract anyway
  c) Cancel — stop here
```

**Wait for user answer.**

- `c` → stop. Say: "Ok, come back when ready."
- `n` → skip to Step 3
- `y` → proceed to Step 2b

---

## Step 2b — Built-in commit flow

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/wrap_up.py" --diff-stat
```

Show the output (changed files summary). Then:

1. Ask: "Commit message? (or press enter to use: `chore: end-of-day checkpoint`)"
2. Use the provided message, or the default if the user pressed enter without typing
3. Run:

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/wrap_up.py" --commit "<message>"
```

Read the output:

- Starts with `COMMITTED:<hash>` → confirm: "Committed `<hash>`." → proceed to Step 3
- Starts with `FAILED:<reason>` → show the error. Ask: "Fix and retry, or skip commit and extract anyway? [retry/skip]"
  - `retry` → return to the top of Step 2b
  - `skip` → proceed to Step 3

---

## Step 3 — Extract today's sessions

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/extract_today.py"
```

Wait for completion. Then say:

```
Sessions saved. Have a good one! 👋
```

---

## Important Constraints

- This skill NEVER calls `/sc:git` or any external plugin or skill.
- Git operations are handled entirely by `scripts/wrap_up.py`.
- Session extraction is handled entirely by `scripts/extract_today.py`.
- Both scripts live in the same plugin directory (`${CLAUDE_PLUGIN_ROOT}/scripts/`).
