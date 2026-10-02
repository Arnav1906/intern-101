#!/usr/bin/env python3
"""Intern 101 Codex helpers. JSON output; Python standard library only."""

import argparse
import json
import re
import sqlite3
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

from lib.codex_sessions import discover, local_time, metadata, prepare
from lib.contexts import already_saved, atomic_write, read_contexts, save
from lib.workspace import belongs_to_project, codex_home, config, inside, project_root


def git(root, *args):
    result = subprocess.run(["git", *args], cwd=str(root), capture_output=True, text=True)
    if result.returncode:
        raise ValueError(result.stderr.strip() or "git command failed")
    return result.stdout.strip()


def session_list(args, root, home):
    sessions, errors = [], []
    target = args.date or (datetime.now().strftime("%Y-%m-%d") if args.today else None)
    for item in discover(home, root, args.include_archived):
        try:
            data = prepare(item, home, root)
            activity = data.get("activity_dates", [data["date"]])
            if target and target not in activity:
                continue
            saved = already_saved(root, data)
            if args.new and saved:
                continue
            sessions.append({k: data[k] for k in ("session_id", "date", "first_ts", "last_ts", "total_user", "total_assistant")})
            sessions[-1].update({"path": item["path"], "extracted": saved,
                                 "preview": next((t["text"][:160] for t in data["turns"] if t["role"] == "user"), "")})
        except (ValueError, OSError, json.JSONDecodeError) as error:
            errors.append({"session_id": item["id"], "error": str(error)})
    sessions.sort(key=lambda x: x["last_ts"], reverse=True)
    return {"project_root": str(root), "codex_home": str(home), "sessions": sessions, "errors": errors}


def select_session(args, root, home):
    if args.path:
        path = Path(args.path).expanduser().resolve()
        meta = metadata(path)
        if not belongs_to_project(meta.get("cwd"), root):
            raise ValueError("Session does not belong to the selected project")
        return {"id": meta.get("id") or meta.get("session_id"), "cwd": meta["cwd"], "path": str(path),
                "history_mode": meta.get("history_mode", "legacy")}
    items = discover(home, root, args.include_archived)
    if args.session:
        items = [x for x in items if x["id"] == args.session]
    if not items:
        raise ValueError("No matching Codex session found")
    if not args.session:
        prepared = [(prepare(x, home, root), x) for x in items]
        return max(prepared, key=lambda pair: pair[0]["last_ts"])[1]
    return items[0]


def status(root):
    result = []
    for path in sorted((root / "projects").glob("*/*_progress.md")):
        inside(root, path)
        text = path.read_text(encoding="utf-8")
        state = re.search(r"^## Status:\s*(.+)$", text, re.M)
        pending = re.findall(r"^- \[ \] (.+)$", text, re.M)
        result.append({"name": path.parent.name, "status": state[1] if state else "UNKNOWN",
                       "done": len(re.findall(r"^- \[x\] ", text, re.M | re.I)), "pending": len(pending),
                       "next": pending[0] if pending else "", "file": str(path)})
    return {"projects": result}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", help="project root or a directory inside it (default: current directory)")
    parser.add_argument("--codex-home", help="override Codex history directory")
    commands = parser.add_subparsers(dest="command", required=True)
    sessions = commands.add_parser("sessions", help="list this project's Codex sessions")
    sessions.add_argument("--today", action="store_true")
    sessions.add_argument("--date")
    sessions.add_argument("--new", action="store_true")
    sessions.add_argument("--include-archived", action="store_true")
    clean = commands.add_parser("prepare", help="clean one session for synthesis")
    choose = clean.add_mutually_exclusive_group()
    choose.add_argument("--session")
    choose.add_argument("--path")
    clean.add_argument("--include-archived", action="store_true")
    clean.add_argument("--output", help="write a prepared JSON snapshot inside the project")
    store = commands.add_parser("save", help="save synthesized notes from a prepared snapshot")
    store.add_argument("--prepared", required=True)
    store.add_argument("--input", required=True, help="JSON with title, summary, accomplishments, decisions, next_steps")
    history = commands.add_parser("catchup")
    history.add_argument("--limit", type=int, default=5)
    recall = commands.add_parser("recall")
    recall.add_argument("query", nargs="?", default="")
    daily = commands.add_parser("daily-update")
    when = daily.add_mutually_exclusive_group()
    when.add_argument("--yesterday", action="store_true")
    when.add_argument("--date")
    commands.add_parser("status")
    commands.add_parser("doctor")
    wrap = commands.add_parser("wrap-up")
    operation = wrap.add_mutually_exclusive_group()
    operation.add_argument("--diff-stat", action="store_true")
    operation.add_argument("--commit", metavar="MESSAGE")
    args = parser.parse_args()
    root = project_root(args.project)
    if args.command in {"sessions", "prepare", "doctor"}:
        home = codex_home(root, args.codex_home)
    if args.command == "sessions":
        result = session_list(args, root, home)
    elif args.command == "prepare":
        result = prepare(select_session(args, root, home), home, root)
        if args.output:
            output = inside(root, root / args.output)
            atomic_write(output, json.dumps(result, ensure_ascii=False, indent=2) + "\n")
            result = {"prepared": str(output), "session_id": result["session_id"], "turns": len(result["turns"])}
    elif args.command == "save":
        snapshot = inside(root, root / args.prepared)
        summary_path = inside(root, root / args.input)
        result = save(root, json.loads(snapshot.read_text(encoding="utf-8")), json.loads(summary_path.read_text(encoding="utf-8")))
    elif args.command == "catchup":
        result = {"sessions": read_contexts(root)[:max(0, args.limit)]}
    elif args.command == "recall":
        query = args.query.lower()
        result = {"sessions": [row for row in read_contexts(root) if query in (row["title"] + " " + " ".join(row["sections"].values())).lower()]}
    elif args.command == "daily-update":
        date = args.date or (datetime.now() - timedelta(days=int(args.yesterday))).strftime("%Y-%m-%d")
        # Continued sessions create new snapshots. Only the latest snapshot of
        # each source/session is used for a given day's report.
        selected, seen = [], set()
        for row in read_contexts(root):
            identity = (row["source"], row["session_id"] or row["filename"])
            if row["date"] == date and identity not in seen:
                selected.append(row)
                seen.add(identity)
        result = {"date": date, "sessions": selected}
    elif args.command == "status":
        result = status(root)
    elif args.command == "doctor":
        result = {"project_root": str(root), "plugin_root": str(Path(__file__).resolve().parent.parent),
                  "codex_home": str(home), "history_available": home.is_dir(), "python": sys.version.split()[0],
                  "config": config(root), "readers": ["rollout-jsonl", "paginated-completion-records", "thread-items-sqlite"]}
    else:
        if args.commit:
            git(root, "add", "-u")
            git(root, "commit", "-m", args.commit)
            result = {"committed": git(root, "rev-parse", "--short", "HEAD"), "untracked": git(root, "ls-files", "--others", "--exclude-standard").splitlines()}
        elif args.diff_stat:
            result = {"diff": git(root, "diff", "--stat"), "staged_diff": git(root, "diff", "--cached", "--stat")}
        else:
            try:
                git(root, "rev-parse", "--is-inside-work-tree")
            except ValueError:
                result = {"status": "NO_REPO"}
            else:
                changes = git(root, "status", "--porcelain").splitlines()
                result = {"status": "DIRTY" if changes else "CLEAN", "files": changes, "branch": git(root, "branch", "--show-current")}
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, sqlite3.Error) as error:
        print(json.dumps({"error": str(error)}), file=sys.stderr)
        sys.exit(1)
