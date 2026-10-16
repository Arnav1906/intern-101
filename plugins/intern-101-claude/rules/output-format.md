# Output Format

Always-on rule. All intern-101 skills must follow these conventions.

## daily-update

- Exactly 5–7 bullet points
- Plain English — no technical jargon, acronyms, or internal system names
- Past tense throughout
- One line per bullet, max 120 characters per bullet
- No sub-bullets

## Context filenames

Pattern: `YYYY-MM-DD-HH-MM-<slug>.md`

- `slug` is a kebab-case summary of the session title
- Max 50 characters for the slug portion
- Example: `2026-05-19-14-32-fix-graph-render-bug.md`

## status output

Render as a markdown table with exactly these columns:

| Sub-project | Status | Last Updated | Next Action |

- Status values: `Active`, `Blocked`, `Complete`, `Paused`
- Last Updated: YYYY-MM-DD
- Next Action: one imperative clause, max 80 chars

## Emoji

Never use emoji in any output unless the user explicitly asked for it in their message.
