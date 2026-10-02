"""Read Codex rollouts (legacy and paginated item-completion records).

Storage formats are private to Codex. Fail explicitly when full conversation
content is unavailable; never treat a history index as a complete transcript.
"""

import hashlib
import json
import re
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path

from .workspace import belongs_to_project


def local_time(value):
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value / 1000 if value > 100000000000 else value).astimezone()
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone()
    except (ValueError, TypeError):
        return None


def records(path):
    with path.open(encoding="utf-8", errors="replace") as stream:
        for line in stream:
            try:
                value = json.loads(line)
            except ValueError:
                # A running session can end in a partially written record.
                continue
            if isinstance(value, dict):
                yield value


def metadata(path):
    for row in records(path):
        if row.get("type") == "session_meta":
            return row.get("payload", {})
    return {}


def _subagent(meta):
    source = meta.get("source", meta.get("thread_source", ""))
    return bool(meta.get("parent_thread_id")) or isinstance(source, dict) and "subagent" in source


def discover(home, root, include_archived=False):
    if not home.is_dir():
        raise ValueError("Codex home not found: {}. Set codex_home in .intern101/config.json.".format(home))
    folders = [home / "sessions"]
    if include_archived:
        folders.append(home / "archived_sessions")
    found = {}
    for folder in folders:
        for path in folder.rglob("*.jsonl") if folder.exists() else []:
            meta = metadata(path)
            if not belongs_to_project(meta.get("cwd"), root) or _subagent(meta):
                continue
            sid = meta.get("id") or meta.get("session_id")
            if sid:
                found[sid] = {"id": sid, "path": str(path), "cwd": meta["cwd"],
                              "history_mode": meta.get("history_mode", "legacy")}
    # Indexes can refer to paginated sessions with no standalone rollout.
    # Use a read-only connection and inspect column names, not a fixed version.
    for db_path in sorted(home.glob("state_*.sqlite"), reverse=True):
        with closing(sqlite3.connect(db_path.as_uri() + "?mode=ro", uri=True)) as db:
            columns = {row[1] for row in db.execute("PRAGMA table_info(threads)")}
            if not {"id", "cwd", "rollout_path"}.issubset(columns):
                continue
            optional = [c for c in ("history_mode", "archived", "source") if c in columns]
            fields = ["id", "cwd", "rollout_path"] + optional
            for row in db.execute("SELECT " + ",".join(fields) + " FROM threads"):
                item = dict(zip(fields, row))
                if not belongs_to_project(item["cwd"], root):
                    continue
                if item.get("archived") and not include_archived:
                    continue
                if "subagent" in str(item.get("source", "")).lower():
                    continue
                sid = item["id"]
                if sid not in found:
                    found[sid] = {"id": sid, "cwd": item["cwd"], "path": item["rollout_path"],
                                  "history_mode": item.get("history_mode", "legacy")}
            break
    return list(found.values())


def _text(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(part.get("text", "") for part in content
                         if isinstance(part, dict) and part.get("type", "").lower() in
                         ("text", "input_text", "output_text", "inputtext", "outputtext"))
    return ""


def _clean_user(text):
    if text.lstrip().startswith(("# AGENTS.md instructions", "<INSTRUCTIONS>")):
        return ""
    text = re.sub(r"<environment_context>.*?</environment_context>", "", text, flags=re.S)
    text = re.sub(r"<skill>.*?</skill>", "", text, flags=re.S)
    if text.lstrip().startswith(("Base directory for this skill:", "<skill")):
        return ""
    if text.strip().lower() in {"ok", "okay", "continue", "proceed", "done"}:
        return ""
    return text.strip()


def _tool(item):
    kind = item.get("type", "").replace("_", "").lower()
    if kind == "commandexecution":
        return "Command: " + str(item.get("command", ""))[:240], []
    if kind == "filechange":
        changes = item.get("changes", [])
        paths = list(changes) if isinstance(changes, dict) else [c.get("path", "") for c in changes if isinstance(c, dict)]
        return "Files changed: " + ", ".join(paths), paths
    if kind in {"functioncall", "customtoolcall"}:
        name = item.get("name", "tool")
        raw = item.get("arguments", item.get("input", ""))
        try:
            args = json.loads(raw) if isinstance(raw, str) else raw
        except ValueError:
            args = raw
        if isinstance(args, dict):
            label = args.get("description") or args.get("cmd") or args.get("command") or args.get("file_path") or ""
        else:
            label = str(args)
        paths = re.findall(r"^\*\*\* (?:Add|Update|Delete) File: (.+)$", str(raw), re.M) if "apply_patch" in name else []
        return "{}: {}".format(name, str(label)[:240]), paths
    return "", []


def _database_items(home, sid):
    for path in sorted(home.glob("thread_history_*.sqlite"), reverse=True):
        with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as db:
            columns = {r[1] for r in db.execute("PRAGMA table_info(thread_items)")}
            if not {"thread_id", "item_json", "rollout_ordinal"}.issubset(columns):
                continue
            timestamp = "created_at_ms" if "created_at_ms" in columns else "NULL"
            result = []
            for raw, ts in db.execute("SELECT item_json," + timestamp + " FROM thread_items WHERE thread_id=? ORDER BY rollout_ordinal", (sid,)):
                result.append({"timestamp": ts, "item": json.loads(raw)})
            if result:
                return result
    return []


def prepare(session, home, root):
    path = Path(session.get("path") or "")
    rows = list(records(path)) if path.is_file() else []
    meta = next((r.get("payload", {}) for r in rows if r.get("type") == "session_meta"), {})
    # response_item messages and item_completed messages overlap. Pick one
    # representation for prose so it is never counted twice.
    response_roles = {r.get("payload", {}).get("role") for r in rows
                      if r.get("type") == "response_item" and r.get("payload", {}).get("type") == "message"
                      and r.get("payload", {}).get("role") in {"user", "assistant"}}
    events = []
    model = ""
    for row in rows:
        p = row.get("payload", {})
        kind = row.get("type")
        if kind == "turn_context":
            model = p.get("model") or model
        elif kind == "response_item":
            events.append({"timestamp": row.get("timestamp"), "item": p})
        elif kind == "event_msg" and p.get("type") == "item_completed":
            item = p.get("item", {})
            if _message(item)[0] in response_roles:
                continue
            events.append({"timestamp": row.get("timestamp"), "item": item})
    if not any(_message(e["item"])[0] for e in events):
        events = _database_items(home, session["id"]) or events
    # Older rollouts may only have event_msg user_message/agent_message records.
    if not any(_message(e["item"])[0] for e in events):
        for row in rows:
            p = row.get("payload", {})
            if row.get("type") == "event_msg" and p.get("type") in {"user_message", "agent_message"}:
                events.append({"timestamp": row.get("timestamp"), "item": {
                    "type": "message", "role": "user" if p["type"] == "user_message" else "assistant",
                    "content": p.get("message", "")}})
    turns, files, times, signatures = [], [], [], []
    for e in events:
        item = e["item"]
        role, prose = _message(item)
        ts = local_time(e.get("timestamp"))
        if role == "user":
            prose = _clean_user(prose)
        label, modified = _tool(item)
        if prose or label:
            signatures.append({"item": item, "timestamp": e.get("timestamp")})
            if ts:
                times.append(ts)
            turns.append({"role": role or "assistant", "hhmm": ts.strftime("%H:%M") if ts else "??:??",
                          "text": prose[:2000], "tools": [label] if label else []})
            files.extend(modified)
    if not any(t["text"] for t in turns):
        raise ValueError("No readable conversation for session {} ({}). This Codex history format may be unsupported.".format(session["id"], session.get("history_mode", "unknown")))
    fallback = local_time(meta.get("timestamp")) or datetime.now().astimezone()
    first, last = (min(times), max(times)) if times else (fallback, fallback)
    digest = hashlib.sha256(json.dumps(signatures, sort_keys=True).encode("utf-8")).hexdigest()
    return {"source": "codex", "session_id": session["id"], "cwd": session["cwd"],
            "project_root": str(root), "date": last.strftime("%Y-%m-%d"),
            "activity_dates": sorted({ts.strftime("%Y-%m-%d") for ts in times} or {fallback.strftime("%Y-%m-%d")}),
            "first_ts": first.isoformat(), "last_ts": last.isoformat(), "fingerprint": digest,
            "model": model, "turns": turns, "files_modified": list(dict.fromkeys(files)),
            "total_user": sum(t["role"] == "user" for t in turns),
            "total_assistant": sum(t["role"] == "assistant" for t in turns)}


def _message(item):
    kind = item.get("type", "").replace("_", "").lower()
    if kind == "message" and item.get("role") in {"user", "assistant"}:
        return item["role"], _text(item.get("content"))
    if kind in {"usermessage", "agentmessage"}:
        return "user" if kind == "usermessage" else "assistant", _text(item.get("content", item.get("text", "")))
    return "", ""
