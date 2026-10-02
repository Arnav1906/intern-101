---
name: wrap-up
description: Finish a work session by reviewing project Git changes, optionally committing them, and saving today's Codex context notes.
---

Read [runtime guidance](../../references/runtime.md). Run `wrap-up` to check Git.

For DIRTY, show changes and offer commit, skip commit, or cancel unless the user
already specified a choice. Before committing, run `wrap-up --diff-stat`, review
what will be included, and obtain or derive a commit message from the authorized
changes. Only then run `wrap-up --commit "<message>"`. It stages tracked changes
with `git add -u`; identify untracked files for the user to include explicitly.
Do not push as part of this workflow.

For CLEAN or NO_REPO, continue with the sibling extract-today skill. If a commit
fails, report the failure and let the user choose retry or extraction without a
commit. Report the commit result and saved context paths.
