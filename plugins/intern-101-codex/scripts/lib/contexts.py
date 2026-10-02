"""Project-local Markdown storage and extraction checkpoints."""

import json
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path

from .workspace import contexts_dir, inside


def atomic_write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, name = tempfile.mkstemp(dir=str(path.parent), prefix=".intern101-", suffix=".tmp")
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def read_contexts(root):
    result = []
    for path in contexts_dir(root).glob("*.md"):
        if path.name == "INDEX.md":
            continue
        inside(root, path)
        text = path.read_text(encoding="utf-8-sig")
        fields = {}
        if text.startswith("---\n"):
            front = text.split("---", 2)[1]
            for line in front.splitlines():
                if ":" in line:
                    key, value = line.split(":", 1)
                    value = value.strip()
                    try:
                        fields[key] = json.loads(value)
                    except ValueError:
                        fields[key] = value
        title = re.search(r"^# (.+)$", text, re.M)
        sections = {}
        for match in re.finditer(r"^## ([^\n]+)\n(.*?)(?=^## |\Z)", text, re.M | re.S):
            sections[match[1]] = match[2].strip()
        result.append({"path": str(path), "filename": path.name,
                       "date": str(fields.get("date", path.name[:10])),
                       "title": title[1] if title else path.stem,
                       "source": fields.get("source", ""),
                       "session_id": fields.get("session_id", ""),
                       "fingerprint": fields.get("fingerprint", ""),
                       "saved_at": fields.get("saved_at", ""), "sections": sections})
    return sorted(result, key=lambda r: (r["date"], str(r["saved_at"]), r["filename"]), reverse=True)


def already_saved(root, session):
    return any(row["source"] == "codex" and row["session_id"] == session["session_id"]
               and row["fingerprint"] == session["fingerprint"] for row in read_contexts(root))


def _table_text(value):
    return " ".join(str(value).replace("|", "-").split())


def _ensure_index(folder, filename, date, title, description):
    index = folder / "INDEX.md"
    content = index.read_text(encoding="utf-8") if index.exists() else "# Chat Context Index\n\n| Date | Title | Filename | Summary |\n|---|---|---|---|\n"
    if "`{}`".format(filename) not in content:
        row = "| {} | {} | `{}` | {} |\n".format(date, _table_text(title), filename, _table_text(description)[:300])
        atomic_write(index, content.rstrip() + "\n" + row)
    return index


def save(root, prepared, summary):
    if prepared.get("source") != "codex" or not prepared.get("session_id") or not prepared.get("fingerprint"):
        raise ValueError("Use a prepared Codex session produced by the prepare command")
    if Path(prepared.get("project_root", "")).resolve() != root:
        raise ValueError("Prepared session belongs to a different project")
    title = summary.get("title")
    description = summary.get("summary")
    accomplishments = summary.get("accomplishments")
    if not isinstance(title, str) or not title.strip() or "\n" in title:
        raise ValueError("title must be a non-empty single line")
    if not isinstance(description, str) or not description.strip():
        raise ValueError("summary must be non-empty text")
    if not isinstance(accomplishments, list) or not all(isinstance(x, str) for x in accomplishments):
        raise ValueError("accomplishments must be an array of strings")
    for field in ("decisions", "next_steps"):
        if not isinstance(summary.get(field, []), list) or not all(isinstance(x, str) for x in summary.get(field, [])):
            raise ValueError("{} must be an array of strings".format(field))
    folder = contexts_dir(root)
    folder.mkdir(parents=True, exist_ok=True)
    # Short exclusive lock covers the document and index transaction. Parallel
    # synthesizers can retry without losing another session's index entry.
    lock = folder / ".intern101-write.lock"
    try:
        descriptor = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise ValueError("Another context save is in progress. Retry after it finishes. If interrupted, inspect and remove {}.".format(lock))
    try:
        os.close(descriptor)
        for existing in read_contexts(root):
            if existing["source"] == "codex" and existing["session_id"] == prepared["session_id"] and existing["fingerprint"] == prepared["fingerprint"]:
                # Recover an interrupted save that created a note but did not
                # yet publish its index row.
                index = _ensure_index(folder, existing["filename"], existing["date"], existing["title"], existing["sections"].get("Summary", ""))
                return {"status": "already_saved", "session_id": prepared["session_id"], "path": existing["path"], "index": str(index)}
        date = prepared.get("date", "")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
            raise ValueError("Invalid prepared session date")
        slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:50].rstrip("-") or "session"
        filename = date + "_" + slug + ".md"
        counter = 2
        while (folder / filename).exists():
            filename = "{}_{}_v{}.md".format(date, slug, counter)
            counter += 1
        metadata = {k: prepared.get(k, "") for k in ("source", "session_id", "date", "model", "fingerprint", "first_ts", "last_ts")}
        metadata["saved_at"] = datetime.now().astimezone().isoformat()
        lines = ["---"] + ["{}: {}".format(k, json.dumps(v)) for k, v in metadata.items()] + ["---", "", "# " + title.strip(), "", "## Summary", description.strip(), ""]
        for heading, bullets in (("Accomplishments", accomplishments), ("Key Decisions & Findings", summary.get("decisions", [])),
                                 ("Next Steps", summary.get("next_steps", [])), ("Files Modified", prepared.get("files_modified", []))):
            if bullets:
                lines.extend(["## " + heading] + ["- " + " ".join(b.split()) for b in bullets] + [""])
        path = folder / filename
        # Exclusive creation preserves existing notes even after a collision.
        with path.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write("\n".join(lines))
        index = _ensure_index(folder, filename, date, title, description)
        return {"status": "saved", "path": str(path), "index": str(index), "session_id": prepared["session_id"]}
    finally:
        lock.unlink()
