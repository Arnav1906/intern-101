---
name: session-manager
description: Orchestrates intern-101 session management skills. Use when a user starts a session (needs catchup), wants to find past work (recall), or needs a combination of session-related operations. Decides context depth and chains skills appropriately.
origin: intern-101
---

## When to activate

- User starts a session: "what was I working on", "let's pick up where we left off", `/catchup`
- User wants to find past work: "did we work on X", "find sessions about Y", `/recall`
- User wants a daily update or end-of-day summary
- User wants a combined project overview

## Decision logic

| Condition | Action |
|-----------|--------|
| Session start, vague or no topic | `catchup` (summary only) |
| Session start with specific topic | `catchup` + `recall(topic)` |
| User wants to write a daily update | Check if today extracted → if not, `extract-today` first, then `daily-update` |
| User wants full project picture | `status` + `catchup` |
| User asks about a past topic only | `recall(topic)` |

## Context depth choices

When loading context, always offer these three options unless the user already specified:

- **Light** — summary only (last session title + one-line status per sub-project)
- **Medium** — summary + key decisions made in recent sessions
- **Full** — summary + decisions + sub-project progress from `_progress.md` files

Default to Light unless the user signals they need more detail.

## Hard rules

- Never load full session transcripts (.jsonl files) unless the user explicitly asks for raw transcript content.
- Always run `extract-today` before `daily-update` if today's sessions have not been extracted yet. Check `chat-contexts/` for files with today's date prefix first.
- Never chain more than three skills in one response without confirming with the user.
