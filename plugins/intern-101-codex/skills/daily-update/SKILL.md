---
name: daily-update
description: Generate a concise supervisor update from today's or yesterday's project context notes, or from notes supplied by the user.
---

Read [runtime guidance](../../references/runtime.md).

For supplied notes, synthesize directly. Otherwise run `daily-update`, passing
`--yesterday` or `--date YYYY-MM-DD` when requested. This includes Accomplishments,
Summary, decisions, and pending work from the project's saved Markdown notes.
If there are no notes for today, follow extract-today and then retry. For older
days offer extraction of a selected session or ask for work notes.

Use the person's name if known; otherwise ask which name to put on the update.
Write `[Name] Daily Update – DD/MM/YY`, followed by 5–7 flat bullets under 200
words total when the evidence supports that many items. Combine related work
and ask for additional notes when too little activity is available. Do not pad.
Describe accomplishments in plain language; prefix blockers with `[BLOCKER]`.
Keep colleague names, business terms, and useful issue links. Deduplicate related
work across sessions. Return the update ready to copy, without extra commentary.
