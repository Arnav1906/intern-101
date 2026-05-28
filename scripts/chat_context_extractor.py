"""Extract a structured markdown context doc from a Claude Code .jsonl session file."""

import sys
import json
import argparse
import re
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from lib.utils import get_chat_contexts_dir, ensure_dir, write_file, now_str
from lib.session import slugify


def _extract_text(content) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    parts.append(block.get("text", "").strip())
                elif block.get("type") == "tool_use":
                    name = block.get("name", "")
                    inp = block.get("input", {})
                    if name == "Write" and "file_path" in inp:
                        parts.append(f"[Write] {inp['file_path']}")
                    elif name == "Edit" and "file_path" in inp:
                        parts.append(f"[Edit] {inp['file_path']}")
                    elif name == "Bash" and "command" in inp:
                        cmd = inp["command"][:120].replace("\n", " ")
                        parts.append(f"[Bash] {cmd}")
        return "\n".join(p for p in parts if p)
    return ""


def parse_jsonl(jsonl_path: Path):
    turns = []
    with jsonl_path.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            msg_type = obj.get("type", "")
            msg = obj.get("message", {})
            if not isinstance(msg, dict):
                continue
            role = msg.get("role", "")
            content = msg.get("content", "")
            text = _extract_text(content)
            if text:
                turns.append({"type": msg_type, "role": role, "text": text})
    return turns


def _files_modified(turns: list) -> list:
    files = []
    seen = set()
    for t in turns:
        if t["role"] != "assistant":
            continue
        for m in re.finditer(r'\[(Write|Edit)\] (.+)', t["text"]):
            path = m.group(2).strip()
            if path not in seen:
                seen.add(path)
                files.append(path)
    return files


def _first_user_message(turns: list) -> str:
    for t in turns:
        if t["role"] == "user" and t["text"].strip():
            return t["text"].strip()
    return ""


def _generate_title(first_msg: str) -> str:
    first_line = first_msg.split("\n")[0].strip()
    first_line = re.sub(r"[#*`]", "", first_line).strip()
    return first_line[:80] or "Untitled Session"


def _collect_summaries(turns: list) -> str:
    user_msgs = [t["text"] for t in turns if t["role"] == "user"]
    assistant_msgs = [t["text"] for t in turns if t["role"] == "assistant"]
    return "\n---\n".join((user_msgs + assistant_msgs)[:6])


def _extract_tags(title: str, files: list) -> str:
    words = re.findall(r'[a-zA-Z]{4,}', title.lower())
    exts = {Path(f).suffix.lstrip(".") for f in files if Path(f).suffix}
    tags = list(dict.fromkeys(words))[:5]
    tags += [e for e in sorted(exts) if e and e not in tags]
    return ", ".join(tags) if tags else "session"


def build_context_doc(jsonl_path: Path, session_id: str, turns: list) -> tuple[str, str]:
    title = _generate_title(_first_user_message(turns))
    date = datetime.now().strftime("%Y-%m-%d")
    files = _files_modified(turns)

    user_tasks = [t["text"] for t in turns if t["role"] == "user"][:3]
    assistant_outputs = [t["text"] for t in turns if t["role"] == "assistant"][:3]

    summary_src = "\n\n".join(user_tasks + assistant_outputs)
    summary_lines = [s.strip() for s in summary_src.split("\n") if len(s.strip()) > 20][:5]
    summary = " ".join(summary_lines[:3]) or "Session recorded."

    decisions = []
    for t in turns:
        if t["role"] != "assistant":
            continue
        for line in t["text"].split("\n"):
            line = line.strip()
            if line.startswith("- ") and len(line) > 10:
                decisions.append(line)
    decisions = decisions[:8]

    tags = _extract_tags(title, files)

    lines = [
        f"---",
        f"session_id: {session_id}",
        f"date: {date}",
        f"---",
        f"",
        f"# {title}",
        f"**Date:** {date}  **Session:** {session_id}",
        f"",
        f"## Summary",
        summary,
        f"",
        f"## Key Decisions & Findings",
    ]
    if decisions:
        lines += decisions
    else:
        lines.append("- No explicit decisions recorded.")
    lines += [
        f"",
        f"## Files Modified",
    ]
    if files:
        lines += [f"- {f}" for f in files]
    else:
        lines.append("- None recorded.")
    lines += [
        f"",
        f"## Tags",
        tags,
    ]
    return title, "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("jsonl_path", help=".jsonl session file path")
    parser.add_argument("--output-dir", default=None, help="output directory (default: cwd/chat-contexts/)")
    args = parser.parse_args()

    jsonl_path = Path(args.jsonl_path).resolve()
    if not jsonl_path.exists():
        print(f"ERROR:file not found: {jsonl_path}", file=sys.stderr)
        sys.exit(1)

    session_id = jsonl_path.stem

    out_dir = Path(args.output_dir).resolve() if args.output_dir else get_chat_contexts_dir(Path.cwd())
    ensure_dir(out_dir)

    turns = parse_jsonl(jsonl_path)
    if not turns:
        print(f"ERROR:no readable turns in {jsonl_path}", file=sys.stderr)
        sys.exit(1)

    title, doc = build_context_doc(jsonl_path, session_id, turns)

    slug = slugify(title)
    ts = now_str()
    out_filename = f"{ts}-{slug}.md"
    out_path = out_dir / out_filename
    write_file(out_path, doc)

    _update_index(out_dir, out_path.name, title)

    print(f"WRITTEN:{out_path}")


def _update_index(ctx_dir: Path, filename: str, title: str) -> None:
    idx_path = ctx_dir / "INDEX.md"
    date = datetime.now().strftime("%Y-%m-%d")
    row = f"| {date} | {title[:60]} | `{filename}` |"
    if not idx_path.exists():
        header = "| Date | Title | Filename |\n|---|---|---|\n"
        write_file(idx_path, header + row + "\n")
    else:
        content = idx_path.read_text(encoding="utf-8")
        if filename not in content:
            write_file(idx_path, content.rstrip() + "\n" + row + "\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR:{e}", file=sys.stderr)
        sys.exit(1)
