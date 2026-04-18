#!/usr/bin/env python3
"""
extract_users.py - Extract user messages from distill-logs for extract analysis.

Usage:
    # Single output to stdout (original behavior):
    python extract_users.py [<logs_dir>] [--files f1 f2 ...] [--max-msg-len 500]

    # Batch mode: split M files into ceil(M/N) batch files, write to output-dir:
    python extract_users.py [<logs_dir>] --files f1 f2 ... --batch-size N --output-dir DIR
"""

import re
import sys
import argparse
from pathlib import Path


def parse_frontmatter(text: str) -> dict:
    if not text.startswith('---'):
        return {}
    end = text.find('\n---', 3)
    if end == -1:
        return {}
    fm_text = text[4:end]
    result = {}
    for line in fm_text.splitlines():
        if ':' in line:
            key, _, val = line.partition(':')
            result[key.strip()] = val.strip()
    return result


def extract_user_messages(text: str) -> list[str]:
    messages = []
    pattern = re.compile(r'\*\*User:\*\*\n(.*?)(?=\n\*\*(?:User|Assistant):\*\*|\Z)', re.DOTALL)
    for m in pattern.finditer(text):
        content = m.group(1).strip()
        if content:
            messages.append(content)
    return messages


def truncate_message(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len] + f'\n[...truncated {len(text) - max_len} chars]'


def format_session(path: Path, fm: dict, messages: list[str], source_tag: str = '') -> str:
    topic = fm.get('topic', path.stem)
    date = fm.get('date', '')[:10]
    tags = fm.get('tags', '[]')
    sentiment = fm.get('sentiment', 'neutral')
    label = f'=== Session: {topic} ({date}) | sentiment: {sentiment} | tags: {tags}'
    if source_tag:
        label += f' | {source_tag}'
    label += ' ==='

    lines = [label]
    for i, msg in enumerate(messages, 1):
        lines.append(f'[Turn {i}] {msg}')
    lines.append('')
    return '\n'.join(lines)


def collect_files(logs_dir: Path, extra_input: str | None,
                  specific_files: list[str] | None = None) -> list[tuple[Path, str]]:
    files = []

    if specific_files is not None:
        for f in specific_files:
            p = Path(f)
            if not p.is_absolute():
                p = logs_dir / f
            if p.exists():
                files.append((p, ''))
        return files

    if logs_dir.exists():
        for f in sorted(logs_dir.glob('*.md')):
            if '_extract_' not in f.name:
                files.append((f, ''))

    if extra_input:
        p = Path(extra_input)
        if p.is_file():
            files.append((p, '外部导入'))
        elif p.is_dir():
            for f in sorted(p.glob('**/*.md')) + sorted(p.glob('**/*.txt')):
                files.append((f, '外部导入'))

    return files


def main():
    parser = argparse.ArgumentParser(description='Extract user messages from distill-logs.')
    parser.add_argument('logs_dir', nargs='?',
                        default=str(Path.home() / '.claude' / 'distill-logs'),
                        help='Path to distill-logs directory')
    parser.add_argument('--input', help='Extra file or directory to include')
    parser.add_argument('--files', nargs='*', default=None,
                        help='Process only these specific files (basenames or full paths)')
    parser.add_argument('--max-msg-len', type=int, default=500,
                        help='Truncate user messages longer than this (default: 500)')
    parser.add_argument('--batch-size', type=int, default=None,
                        help='Split into batches of this size and write to --output-dir')
    parser.add_argument('--output-dir', default=None,
                        help='Directory to write batch files (used with --batch-size)')
    args = parser.parse_args()

    logs_dir = Path(args.logs_dir)
    files = collect_files(logs_dir, args.input, args.files)

    if not files:
        print('No log files found.', file=sys.stderr)
        sys.exit(1)

    dates = []
    output_parts = []

    for path, source_tag in files:
        try:
            text = path.read_text(encoding='utf-8')
        except Exception as e:
            print(f'Warning: could not read {path}: {e}', file=sys.stderr)
            continue

        fm = parse_frontmatter(text)
        messages = extract_user_messages(text)

        if not messages:
            continue

        if args.max_msg_len:
            messages = [truncate_message(m, args.max_msg_len) for m in messages]

        if fm.get('date'):
            dates.append(fm['date'][:10])

        output_parts.append(format_session(path, fm, messages, source_tag))

    date_range = f'{min(dates)} ~ {max(dates)}' if dates else 'unknown'
    total = len(output_parts)

    if args.batch_size:
        output_dir = Path(args.output_dir) if args.output_dir else logs_dir / '_extract_batches'
        output_dir.mkdir(parents=True, exist_ok=True)

        batches = [output_parts[i:i + args.batch_size]
                   for i in range(0, len(output_parts), args.batch_size)]
        batch_count = len(batches)
        batch_files = []

        for i, batch in enumerate(batches, 1):
            batch_file = output_dir / f'_batch_{i:03d}.txt'
            header = (f'# Extract Batch {i}/{batch_count} — {len(batch)} sessions ({date_range})\n'
                      f'# Generated by extract_users.py\n\n')
            batch_file.write_text(header + '\n'.join(batch), encoding='utf-8')
            batch_files.append(str(batch_file))

        print(f'Generated {batch_count} batch files (total {total} sessions, batch-size {args.batch_size}):')
        for f in batch_files:
            print(f'  {f}')
    else:
        print(f'# Extract Input — {total} sessions ({date_range})')
        print(f'# Generated by extract_users.py for self-distill default mode')
        print()
        for part in output_parts:
            print(part)


if __name__ == '__main__':
    main()
