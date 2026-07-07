"""Clean a Claude Code .jsonl session transcript to lean JSON for the synthesis agent."""

import sys
import json
import re
import os
from datetime import datetime, timezone
from pathlib import Path

TOOL_KEEP = {
    'Read', 'Write', 'Bash', 'Edit', 'Grep', 'Glob', 'Agent',
    'ExitPlanMode', 'AskUserQuestion', 'WebFetch', 'WebSearch',
}

SKIP_PHRASES = {
    '[request interrupted by user]', 'continue', 'continue.', 'ok', 'okay',
    'done', 'proceed', 'continue from where you left off.',
    'continue from where you left off',
}


def _is_skill_injection(text):
    if text.startswith("Base directory for this skill:"):
        return True
    if re.match(r'^#\s+.+\n.*##\s+Step', text, re.MULTILINE):
        return True
    return False


def _summarise_tool(name, inp):
    if name == 'Read':
        return "Read {}".format(inp.get('file_path', ''))
    if name in ('Write', 'Edit'):
        fp = inp.get('file_path', '')
        desc = inp.get('description', '')
        return "{} {}{}".format(name, fp, " [{}]".format(desc[:60]) if desc else "")
    if name == 'Bash':
        label = inp.get('description', '') or inp.get('command', '')[:120]
        return "Bash: {}".format(label)
    if name == 'Grep':
        return "Grep pattern={}".format(inp.get('pattern', '')[:60])
    if name == 'Glob':
        return "Glob {} in {}".format(inp.get('pattern', ''), inp.get('path', '')[:40])
    if name == 'Agent':
        label = inp.get('description', '') or inp.get('prompt', '')
        return "Agent: {}".format(label[:80])
    if name in ('WebFetch', 'WebSearch'):
        label = inp.get('url', '') or inp.get('query', '')
        return "{}: {}".format(name, label[:80])
    return name


def _files_modified(tool_summaries):
    seen, files = set(), []
    for s in tool_summaries:
        m = re.match(r'^(?:Write|Edit)\s+(.+?)(?:\s+\[|$)', s)
        if m:
            p = m.group(1).strip()
            if p and p not in seen:
                seen.add(p)
                files.append(p)
    return files


def _ts_to_hhmm(ts):
    if not ts:
        return '??:??'
    try:
        dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
        return dt.astimezone(timezone.utc).strftime('%H:%M')
    except Exception:
        return ts[11:16] if len(ts) >= 16 else '??:??'


def _ts_to_date(ts):
    if not ts:
        return ''
    try:
        dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d')
    except Exception:
        return ts[:10] if len(ts) >= 10 else ''


def _clean_user_text(text):
    for pat in [
        r'<command-name>.*?</command-name>',
        r'<command-message>.*?</command-message>',
        r'<command-args>.*?</command-args>',
        r'<local-command-stdout>.*?</local-command-stdout>',
        r'<[a-z][a-z0-9_-]*(?:\s[^>]*)?>.*?</[a-z][a-z0-9_-]*>',
    ]:
        text = re.sub(pat, '', text, flags=re.DOTALL)
    return text.strip()


def main():
    if len(sys.argv) < 2:
        print("ERROR:usage: chat_context_extractor.py <path.jsonl>", file=sys.stderr)
        sys.exit(1)

    jsonl_path = Path(sys.argv[1]).resolve()
    if not jsonl_path.exists():
        print("ERROR:file not found: {}".format(jsonl_path), file=sys.stderr)
        sys.exit(1)

    session_id = ''
    custom_title = ''
    model = ''
    first_ts = ''
    last_ts = ''
    turns = []
    all_tool_summaries = []
    sessions_seen = set()

    with jsonl_path.open(encoding='utf-8', errors='replace') as fh:
        for raw in fh:
            raw = raw.strip()
            if not raw:
                continue
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError:
                continue

            if obj.get('isSidechain', False):
                continue

            t = obj.get('type', '')
            ts = obj.get('timestamp', '')
            if ts:
                if not first_ts or ts < first_ts:
                    first_ts = ts
                if not last_ts or ts > last_ts:
                    last_ts = ts

            sid = obj.get('sessionId', '')
            if sid:
                sessions_seen.add(sid)
                session_id = sid

            if t == 'custom-title':
                custom_title = obj.get('customTitle', '')
                continue
            if t not in ('user', 'assistant'):
                continue

            msg = obj.get('message', {})
            if not isinstance(msg, dict):
                continue
            content = msg.get('content', [])

            if t == 'assistant':
                if not model:
                    model = msg.get('model', '')
                texts, tool_summaries = [], []
                if isinstance(content, list):
                    for item in content:
                        if not isinstance(item, dict):
                            continue
                        ct = item.get('type', '')
                        if ct == 'text':
                            texts.append(item.get('text', ''))
                        elif ct == 'tool_use':
                            name = item.get('name', '')
                            inp = item.get('input', {}) or {}
                            if name in TOOL_KEEP:
                                summary = _summarise_tool(name, inp)
                                tool_summaries.append(summary)
                                all_tool_summaries.append(summary)
                elif isinstance(content, str):
                    texts.append(content)

                prose = ' '.join(x for x in texts if x.strip())[:1200]
                if prose.strip() or tool_summaries:
                    turns.append({
                        'role': 'assistant',
                        'hhmm': _ts_to_hhmm(ts),
                        'text': prose,
                        'tools': tool_summaries,
                    })

            elif t == 'user':
                if isinstance(content, str):
                    cleaned = _clean_user_text(content)
                elif isinstance(content, list):
                    parts = [
                        _clean_user_text(i.get('text', ''))
                        for i in content
                        if isinstance(i, dict) and i.get('type') == 'text'
                    ]
                    cleaned = ' '.join(p for p in parts if p)
                else:
                    cleaned = ''

                if not cleaned:
                    continue
                if cleaned.lower() in SKIP_PHRASES:
                    continue
                if _is_skill_injection(cleaned):
                    continue
                if re.match(r'^\[image\s*[:#]', cleaned, re.IGNORECASE):
                    continue

                turns.append({
                    'role': 'user',
                    'hhmm': _ts_to_hhmm(ts),
                    'text': cleaned[:600],
                })

    if not turns:
        print("ERROR:no readable turns in {}".format(jsonl_path), file=sys.stderr)
        sys.exit(1)

    print(json.dumps({
        'session_id': session_id,
        'custom_title': custom_title,
        'model': model,
        'date': _ts_to_date(first_ts),
        'first_ts': first_ts,
        'last_ts': last_ts,
        'turns': turns,
        'files_modified': _files_modified(all_tool_summaries),
        'session_count': len(sessions_seen),
        'project_root': os.getcwd(),
        'total_user': sum(1 for t in turns if t['role'] == 'user'),
        'total_assistant': sum(1 for t in turns if t['role'] == 'assistant'),
    }))


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print("ERROR:{}".format(e), file=sys.stderr)
        sys.exit(1)
