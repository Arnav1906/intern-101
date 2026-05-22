---
name: intern
description: Main dispatcher for intern-101. Use when the user types /intern or says anything that maps to intern-101 capabilities: session catchup, daily updates, project status, session extraction, knowledge graphs, or end-of-day wrap-up.
origin: intern-101
user-invocable: true
allowed-tools: [Read, Bash]
---

# /intern — Dispatcher

Routes natural language to the right intern-101 skill.

## When to Activate

Trigger on `/intern` or any phrase like:

- "where was I", "catch me up", "what was I working on", "let's resume"
- "write my daily update", "what did I do today", "status report for my supervisor"
- "extract today", "save today's sessions"
- "find sessions about X", "did we work on X before", "recall X"
- "show me project status", "what's the state of everything"
- "set up indexes", "organize the project", "project index"
- "visualise", "graph the codebase", "knowledge map", "map relationships", "architecture overview"
- "I'm done", "done for today", "wrapping up", "signing off", "that's it for today", "I'm finished", "end of day"

## Routing Table

Identify the user's intent and invoke the corresponding skill:

| Intent | Skill |
|---|---|
| "catchup", "where was I", "last session", "resume" | invoke `catchup` skill |
| "daily update", "status report", "what did I do today" | invoke `daily-update` skill |
| "extract today", "save today's sessions" | invoke `extract-today` skill |
| "recall", "find session", "did we work on X" | invoke `recall` skill |
| "status", "all projects", "project overview" | invoke `status` skill |
| "project index", "organize projects", "set up index" | invoke `project-index-manager` skill |
| "graph", "visualise", "knowledge map", "map the codebase" | invoke `visualise` skill |
| "I'm done", "done for today", "wrapping up", "signing off", "that's it for today", "I'm finished", "end of day" | invoke `wrap-up` skill |

## Fallback

If the intent does not clearly map to any of the above, list the available skills and ask the user to clarify:

```
I can help with:

  /catchup            — resume from your last session
  /daily-update       — generate a supervisor status update
  /extract-today      — save today's Claude sessions as context docs
  /recall <query>     — find past sessions about a topic
  /status             — overview of all sub-project statuses
  /project-index-manager — organize a project into indexed sub-projects
  /visualise [path]   — build a knowledge graph of a codebase
  /wrap-up            — end-of-day git check + session extraction

What would you like to do?
```
