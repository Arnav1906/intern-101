---
name: status
description: Show completion counts, pending work, and next actions from the current project's sub-project progress files.
---

Read [runtime guidance](../../references/runtime.md). Run `status`.
Render a table with Sub-Project, Status, Done, Pending, and Next Action.
Flag missing status lines as UNKNOWN. An empty result means project progress
files have not been set up; offer project-index-manager.

For a requested drill-down, read that project's progress file and optionally
its index. Preserve reported blockers and do not infer completed work from
unchecked items.
