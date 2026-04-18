**Language:** **English** | [简体中文](README.md)

# self-distill

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white)

> Your conversation habits with AI are uniquely yours.  
> Other people's skill templates never quite fit, but you don't know where to start writing your own.  
> self-distill finds the answers in your past conversations.

A meta-tool that discovers, distills, and generates personalized skills from your own conversation history.

---

## Why this tool exists

This tool started as a solution to my own problem.

After using Claude Code for a while, I noticed I kept doing the same things: re-explaining the same constraints, correcting the same directions, adding the same context. All of this could have been captured in a skill once and for all — but the problem was, I didn't know what to write.

I tried organizing things manually, but it was too subjective. I'd include things I *thought* were useful while missing the patterns that actually recurred.

There are similar tools out there: Hermes skill-factory can fully automatically analyze and generate skills; Claude Code's built-in `/insights` generates an HTML report with friction points and behavioral metrics. But both share the same problem — **no filtering mechanism**. Every conversation enters analysis indiscriminately, and noise from low-quality sessions dilutes the real signal, leading to skills that miss the mark.

So self-distill's core principle is: **semi-automatic, with you in control.**

You decide which sessions are worth archiving. The AI finds the patterns in those archives.

---

## Key features

- **Near-zero token record**: Archiving is done by a script that directly parses Claude Code's native JSONL files — almost no token cost, safe to call even at 95% context usage
- **Positive/negative tagging**: Mark sessions with `--positive` / `--negative` when recording; negative sessions (with correction behavior) get higher weight in analysis — the most direct signal for skill needs
- **Three-question filter**: Before generating candidates, extract automatically filters out "things Claude already knows" and "one-off needs" — only patterns worth solidifying remain
- **Skill + memory dual output**: Behavior preference candidates don't get forced into skills; instead, they're suggested for memory, confirmed by you

---

## What it is / what it isn't

| ✅ Is | ❌ Is not |
|------|--------|
| Helps you discover what skills or memory you need | Writes a specific skill for you (that's skill-creator) |
| Cross-conversation pattern mining | Fully automatic, no intervention needed |
| Semi-automatic, user-driven filtering | Only outputs skills |

---

## Workflow

```
You filter             Script extracts         AI analyzes
sessions worth   →     zero-token archive  →   cross-session aggregation
archiving               ↓                            ↓
     ↓             distill-logs/              [extract]
  [record]                                          ↓
                                        full candidate list (sorted by demand strength)
                                                    ↓
                                               [apply]
                                          ↙            ↘
                                   generate skill   write to memory
```

Three commands form a closed loop. Each step can be used independently.

---

## Installation

### Claude Code

```bash
cd ~/.claude/skills/
git clone https://github.com/IRUJONEU/claude-code-self-distill self-distill
```

Claude Code automatically discovers skills under `~/.claude/skills/` — no extra configuration needed.

### Claude.ai (Web)

Compress the `self-distill/` directory as `.zip`, rename it to `.skill`, and upload it at Settings > Skills.

---

## Requirements

- Python 3.10+ (standard library only, no extra packages needed)
- Claude Code (record mode requires access to local JSONL files)

---

## Usage

### record — archive the current conversation

Run at the end of a valuable conversation. Archiving is done by the script — **near-zero token cost**, safe to call at any context level.

```
/self-distill record
```

The AI infers the topic automatically, runs `record.py` to parse the current session's JSONL, and writes to:

```
~/.claude/distill-logs/YYYY-MM-DD_HH-MM_<topic>.md
```

#### Tag conversation quality (optional)

```
/self-distill record --positive   # good experience
/self-distill record --negative   # frustrating, with corrections
```

Negative sessions get ×1.5 weight in extract analysis, because correction behavior is the most direct signal for skill needs. Untagged sessions default to neutral.

---

### extract — distill high-frequency skill needs

Run after accumulating a batch of archives, for cross-session pattern analysis. **Recommended in a fresh session** to ensure sufficient context budget.

#### Default mode

```
/self-distill extract
```

In default mode: the AI calls `extract_users.py` to extract user messages from all archives into a compact text, then analyzes that text — **does not read assistant replies, lower token cost**.

#### Full mode

The AI reads the complete conversation (including assistant replies), useful when you have few archives (< 10) or need to capture implicit patterns:

```
/self-distill extract --full
```

#### Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--full` | AI reads full conversation including assistant replies | User messages only |
| `--input <path>` | Import additional conversation files or directories | distill-logs only |

#### Cold start: import from existing history

Use `--input` to import existing conversations directly (Claude.ai exports, manually organized text), skipping the record phase:

```
/self-distill extract --input ~/Downloads/exported-chats/
/self-distill extract --input ~/Downloads/chat-export.txt
```

#### How extract filters candidates

Before generating candidates, the AI applies a three-question filter. **The following types are excluded:**

1. **Things Claude already knows** (general programming, standard tool usage, etc.) → no skill needed
2. **One-off needs** (tightly bound to a specific project, won't recur) → not worth solidifying
3. **Behavior preferences** (constraints like "don't add unnecessary comments") → better suited for memory, listed separately

#### Incremental tracking

Before each extract run, the AI compares the existing `_extract_*.md` against current archives and only processes new sessions, reporting: "X total sessions, Y already processed, Z new."

This design prevents context from blowing up as archives accumulate — re-reading all sessions every time would grow linearly and quickly hit limits. In incremental mode, the AI only reads the small batch of new sessions; previous analysis is read from `_extract_*.md` and merged in. New evidence strengthens existing candidates, new patterns are appended, and nothing from prior runs is lost.

#### Output format

All candidates that pass the three-question filter are **kept in full**, sorted by demand strength — no arbitrary cutoff, every valid finding is preserved.

```
## Skill Candidate #N: <name>
- Trigger: when do you repeatedly need this
- Core content: what should this skill tell the AI
- Evidence: which sessions it appeared in (date + topic)
- Demand strength: ★★★☆☆
```

Results are saved to `~/.claude/distill-logs/_extract_YYYY-MM-DD.md`, containing: Skill candidates, Memory candidates, and **Analysis Notes** (the AI's reasoning about classification decisions, boundary judgments, and why certain patterns were filtered). Multiple runs **merge and update** — historical evidence is never lost.

#### Example output

Real output from running extract on 17 archived sessions:

> **Example extract output** — distilled from 17 sessions
>
> **Skill Candidate #1: Session Handoff Documentation** ★★★★★
> - Trigger: when context is nearing its limit, or at a natural handoff point
> - Core content: Claude should proactively write current status / completed /
>   pending / key decisions / file locations / next steps into
>   a project docs MD, complete enough that a new session can pick up seamlessly
> - Evidence: 7/17 sessions (xxx, xxx, xxx, xxx, etc.)
>
> **Memory Candidates**
>
> | # | Pattern | Strength | Evidence |
> |---|---------|----------|----------|
> | 1 | Maintain PLAN.md — update after each phase | ★★★★☆ | 4 sessions |
> | 2 | Let user execute risky ops — give steps, don't run | ★★★☆☆ | 3 sessions |
> | 3 | Establish shared understanding first — summarize before reading files | ★★★☆☆ | 4 sessions |
> | 4 | Skip obvious confirmations — act when intent is clear | ★★☆☆☆ | 1 session (correction) |
> | 5 | Always reply in Chinese — don't switch because logs/code are in another language | ★★☆☆☆ | 2 sessions (correction) |
>
> 1 skill candidate + 5 memory candidates.
> Proceed to \[apply\] to generate SKILL.md / write to memory?

---

### apply — generate skills or update memory

Run after confirming extract results, to turn candidates into actual files.

```
/self-distill apply
```

The AI reads the latest `_extract_*.md`, lists all candidates, and you choose which ones to generate (enter numbers or "all").

#### Skill generation

If [skill-creator](https://github.com/IRUJONEU/claude-code-skill-creator) is installed: the AI calls `/skill-creator` automatically for higher quality output.

If not installed: the AI uses a built-in process; on first run it will ask if you want to install it. Choose `never` to skip the prompt permanently.

**Either way, the AI shows you the content for confirmation before writing any files.**

Generated skills are written to: `~/.claude/skills/<skill-name>/SKILL.md`

#### Memory candidate handling

Patterns identified as "behavior preferences" in extract are listed separately, and you decide whether to write them to memory:

```
The following patterns are better suited for memory than skills.
Add to ~/.claude/memory/?
- Preference #1: don't add a summary paragraph at the end of responses
- Preference #2: code comments should only explain why, not what
```

After confirmation, they are written to `~/.claude/memory/`, where Claude Code will automatically load them in future conversations.

---

## File structure

```
~/.claude/
├── skills/
│   └── self-distill/
│       ├── SKILL.md
│       ├── scripts/
│       │   ├── record.py           # JSONL → distill log
│       │   └── extract_users.py    # extract user messages for AI analysis
│       └── references/             # format specification docs
└── distill-logs/                   # archive directory (auto-created)
    ├── 2026-04-18_14-30_topic.md   # generated by record
    └── _extract_2026-04-20.md      # generated by extract
```

---

## Design decisions

### Why does record use a script instead of AI?

Two reasons:

1. **Context safety**: Context usage is highest near the end of a conversation — exactly when you most want to record. If record consumed tokens, triggering it at high context would cause an immediate compact, compressing the content you just archived.
2. **Accuracy**: Claude Code natively stores all conversations as JSONL. The script parses them directly — your exact words, character for character, with no AI paraphrase and no drift.

### Why is summarization deferred to the extract phase?

Record only archives. Summarization and analysis are deferred to extract. This keeps record extremely lightweight and safe to call at any time. Extract is a batch operation you initiate intentionally, with a full context budget — the right time for deep analysis.

### Why semi-automatic instead of fully automatic?

Conversation quality determines analysis quality. If every conversation is automatically included, noise from low-quality sessions dilutes the real signal.

You decide which conversations are worth archiving — this isn't extra overhead, it's the quality gate.

---

## License

MIT
