---
name: intern
description: Route requests for session catchup, daily work updates, saved chat context, recall, project status, organization, or end-of-day wrap-up through Intern 101.
---

Read [runtime guidance](../../references/runtime.md), then read the matching
sibling skill's `SKILL.md` and follow its workflow.

| User intent | Skill folder |
|---|---|
| Resume work or ask where they stopped | `catchup` |
| Save today's Codex sessions | `extract-today` |
| Extract a specific session | `chat-context-extractor` |
| Write a daily work update | `daily-update` |
| Find previous work about a topic | `recall` |
| Review sub-project progress | `status` |
| Organize project indexes | `project-index-manager` |
| Finish work for the day | `wrap-up` |

For a combined request, follow the relevant workflows in order. Saving sessions
precedes generating an update from them. If intent is ambiguous, give a short
list of relevant choices.
