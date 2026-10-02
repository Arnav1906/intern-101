---
name: project-index-manager
description: Organize a project into domain-based sub-project indexes and progress files, or maintain those files after work changes.
---

Read [runtime guidance](../../references/runtime.md). Inspect project files,
existing notes, and Git history to identify work domains. Propose groupings and
get agreement before moving existing files.

Create `projects/<name>/<name>_Index.md` describing the domain, key files, and
relevant chat-context notes. Create `<name>_progress.md` with `## Status:`, Done
checkboxes, Pending checkboxes, and Key Gotcha. Populate from actual evidence.
Keep shared configuration, repository metadata, build artifacts, and
`chat-contexts/` at the root.

Create a root `_Index.md` linking the sub-projects and explaining shared folders.
Add a short instruction to the project's `AGENTS.md` to read `_Index.md` when
orienting to this project; preserve all existing instructions. Track any agreed
file moves in `restructure_progress.md` and verify references after moving.

For maintenance requests, update only the relevant index and progress entries.
Use the chat-context-extractor skill when the user wants the session saved.
