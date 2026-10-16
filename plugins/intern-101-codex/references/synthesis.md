# Synthesize a session

The synthesis instructions are the verbatim packaged
[`agents/chat-context-extractor.md`](../agents/chat-context-extractor.md).
Read that complete file and pass its instructions to a native Codex subagent
together with the complete cleaned-session JSON returned by
`scripts/chat_context_extractor.py`. Preserve the skill's supplied prompt
prefix and wait for the agent's original confirmation block.

The packaged agent defines the title and slug rules, output path and version
suffixes, Summary, Accomplishments, optional Key Decisions & Findings, Next Steps
and Files Modified sections, the document frontmatter, and the `INDEX.md` row.
Use those instructions verbatim. The agent writes the Markdown document and
updates the index directly, as the original workflow prescribes.

For batch extraction, preserve the selected-session confirmation, delegate one
task per confirmed session, and collect all returned confirmation blocks in the
original summary template. Native tool binding, concurrency, configured model
inheritance, and unavailable-tool handling are in the
[runtime reference](runtime.md). Do not replace this workflow with `prepare` or
`save` commands, a paging loop, or persistent prepared/synthesis JSON files.
