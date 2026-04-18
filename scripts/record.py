#!/usr/bin/env python3
"""
record.py - Extract Claude Code conversation from JSONL and format as distill log.

Usage:
    python record.py [--file <jsonl_path>] [--project <cwd>] [--output <md_path>]

Auto-detects current project from CWD if --file not specified.
Outputs a draft log with user text verbatim and assistant text included.
The Session 总结 section is left as a placeholder for AI to fill in.
"""

import json
import re
import sys
import os
import argparse
from pathlib import Path
from datetime import datetime, timezone


SYSTEM_TAG_PATTERNS = [
    r'<system-reminder>.*?</system-reminder>',
    r'<ide_opened_file>.*?</ide_opened_file>',
    r'<ide_selection>.*?</ide_selection>',
    r'<user-prompt-submit-hook>.*?</user-prompt-submit-hook>',
    # catch all <command-*> and <local-command-*> family tags
    r'<(?:local-command|command)[-\w]*>.*?</(?:local-command|command)[-\w]*>',
]


def extract_skill_invocation(text: str) -> str | None:
    """If text is a skill injection block, return compact invocation string or None."""
    if not text.startswith('Base directory for this skill:'):
        return None
    first_line = text.split('\n')[0]
    skill_path = first_line.replace('Base directory for this skill:', '').strip()
    skill_name = skill_path.rstrip('/').split('/')[-1]
    args_match = re.search(r'\nARGUMENTS:\s*(.+)', text)
    args = args_match.group(1).strip() if args_match else ''
    return f'/{skill_name} {args}' if args else f'/{skill_name}'


def extract_local_command(text: str) -> str | None:
    """If text is a local command block, return compact representation or None."""
    if '<local-command-caveat>' not in text:
        return None
    name_match = re.search(r'<command-name>(.*?)</command-name>', text, re.DOTALL)
    cmd = name_match.group(1).strip() if name_match else 'unknown'
    return f'[local: {cmd}]'


def clean_user_text(text: str) -> str:
    skill_invocation = extract_skill_invocation(text)
    if skill_invocation is not None:
        return skill_invocation
    local_cmd = extract_local_command(text)
    if local_cmd is not None:
        return local_cmd
    for pattern in SYSTEM_TAG_PATTERNS:
        text = re.sub(pattern, '', text, flags=re.DOTALL)
    return text.strip()


def find_latest_jsonl(cwd: str) -> Path | None:
    slug = re.sub(r'[/._]', '-', cwd)
    project_dir = Path.home() / '.claude' / 'projects' / slug
    if not project_dir.exists():
        return None
    jsonl_files = [f for f in project_dir.glob('*.jsonl')]
    if not jsonl_files:
        return None
    return max(jsonl_files, key=lambda f: f.stat().st_mtime)


def parse_messages(jsonl_path: Path) -> list[dict]:
    messages = []
    with open(jsonl_path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            msg_type = obj.get('type')

            if msg_type == 'user':
                content = obj.get('message', {}).get('content', [])
                parts = []
                for c in (content if isinstance(content, list) else []):
                    if c.get('type') == 'text':
                        cleaned = clean_user_text(c['text'])
                        if cleaned:
                            parts.append(cleaned)
                text = '\n'.join(parts).strip()
                if text:
                    messages.append({
                        'role': 'user',
                        'text': text,
                        'timestamp': obj.get('timestamp', ''),
                    })

            elif msg_type == 'assistant':
                content = obj.get('message', {}).get('content', [])
                parts = []
                for c in (content if isinstance(content, list) else []):
                    if c.get('type') == 'text':
                        t = c.get('text', '').strip()
                        if t:
                            parts.append(t)
                text = '\n'.join(parts).strip()
                if text:
                    messages.append({
                        'role': 'assistant',
                        'text': text,
                        'timestamp': obj.get('timestamp', ''),
                    })

    return messages


def pair_turns(messages: list[dict]) -> list[tuple]:
    """Group messages into (user, assistant) turns. Last user turn may have no assistant."""
    turns = []
    i = 0
    while i < len(messages):
        if messages[i]['role'] == 'user':
            user_msg = messages[i]
            assistant_msg = None
            if i + 1 < len(messages) and messages[i + 1]['role'] == 'assistant':
                assistant_msg = messages[i + 1]
                i += 2
            else:
                i += 1
            turns.append((user_msg, assistant_msg))
        else:
            i += 1
    return turns


def format_log(turns: list[tuple], jsonl_path: Path, topic: str, sentiment: str = 'neutral') -> str:
    first_ts = turns[0][0]['timestamp'] if turns else ''
    if first_ts:
        dt = datetime.fromisoformat(first_ts.replace('Z', '+00:00'))
        date_str = dt.strftime('%Y-%m-%d %H:%M')
        date_header = dt.strftime('%Y-%m-%d')
    else:
        date_str = datetime.now().strftime('%Y-%m-%d %H:%M')
        date_header = datetime.now().strftime('%Y-%m-%d')

    lines = [
        f'---',
        f'date: {date_str}',
        f'topic: {topic}',
        f'turns: {len(turns)}',
        f'sentiment: {sentiment}',
        f'tags: []',
        f'---',
        f'',
        f'# {topic} — {date_header}',
        f'',
        f'## 元信息',
        f'- 总轮次：{len(turns)} 轮',
        f'- Session 文件：{jsonl_path.name}',
        f'',
        f'---',
        f'',
        f'## 对话记录',
        f'',
    ]

    for i, (user_msg, assistant_msg) in enumerate(turns, 1):
        lines.append(f'### Turn {i}')
        lines.append(f'')
        lines.append(f'**User:**')
        lines.append(user_msg['text'])
        lines.append(f'')

        if assistant_msg:
            lines.append(f'**Assistant:**')
            lines.append(assistant_msg['text'])
        else:
            lines.append(f'**Assistant:** [无回复]')

        lines.append(f'')
        lines.append(f'---')
        lines.append(f'')

    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='Extract Claude Code conversation to distill log.')
    parser.add_argument('--file', help='Path to JSONL file')
    parser.add_argument('--project', default=os.getcwd(), help='Project CWD (for auto-detect, default: current dir)')
    parser.add_argument('--output', help='Output markdown file path')
    parser.add_argument('--topic', default='', help='Topic name for the log file')
    sentiment_group = parser.add_mutually_exclusive_group()
    sentiment_group.add_argument('--positive', action='store_true', help='Mark session as positive experience')
    sentiment_group.add_argument('--negative', action='store_true', help='Mark session as negative experience')
    args = parser.parse_args()

    if args.positive:
        sentiment = 'positive'
    elif args.negative:
        sentiment = 'negative'
    else:
        sentiment = 'neutral'

    if args.file:
        jsonl_path = Path(args.file)
    else:
        jsonl_path = find_latest_jsonl(args.project)
        if not jsonl_path:
            print(f'ERROR: No JSONL found for project: {args.project}', file=sys.stderr)
            sys.exit(1)

    print(f'Reading: {jsonl_path}', file=sys.stderr)
    messages = parse_messages(jsonl_path)
    turns = pair_turns(messages)
    print(f'Found {len(messages)} messages, {len(turns)} turns', file=sys.stderr)

    topic = args.topic or 'untitled'
    content = format_log(turns, jsonl_path, topic, sentiment)

    if args.output == '-':
        print(content)
    else:
        if args.output:
            output_path = Path(args.output)
        else:
            first_ts = turns[0][0]['timestamp'] if turns else ''
            if first_ts:
                dt = datetime.fromisoformat(first_ts.replace('Z', '+00:00'))
                filename = dt.strftime(f'%Y-%m-%d_%H-%M_{topic}.md')
            else:
                filename = f'{datetime.now().strftime("%Y-%m-%d_%H-%M")}_{topic}.md'
            output_path = Path.home() / '.claude' / 'distill-logs' / filename
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding='utf-8')
        print(output_path)


if __name__ == '__main__':
    main()
