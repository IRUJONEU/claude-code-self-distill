**Language:** **English** | [简体中文](README.zh-CN.md)

# self-distill

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white)

> Your conversation habits with AI are uniquely yours.  
> Other people's skill templates never quite fit, but you don't know where to start writing your own.  
> Self-distill helps you find answers from conversations, but you take the lead.

A meta-tool that discovers, distills, and generates personalized skills from your own conversation history.

The routine is simple: run `/self-distill record` at the end of a useful conversation (If the experience is not satisfactory, add `--negative`.), then periodically run `/self-distill extract` in a fresh session. That's it — a **user-driven** closed loop that stays out of your way.

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
- **Five-question filter**: Before generating candidates, extract automatically filters out "things Claude already knows" and "one-off needs", and distinguishes hook candidates (need system-level auto-triggering), memory candidates (behavior preferences), and CLAUDE.md candidates (always-active global rules) — only patterns that genuinely need a skill reach the skill candidate list
- **Skill + hook + memory + CLAUDE.md four outputs**: Behavior preference candidates are suggested for memory; patterns that need to fire on system events are suggested as hooks; always-active global behavioral rules are suggested for CLAUDE.md; all confirmed by you before being written

---

## What it is / what it isn't

| ✅ Is | ❌ Is not |
|------|--------|
| Helps you discover what skills, hooks, or memory you need | Writes a specific skill for you |
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
                             ↙          ↓           ↓              ↘
                       generate skill  configure hook  write to memory  write to CLAUDE.md
```

Three commands form a closed loop. Each step can be used independently.

---

## Installation

### Claude Code

**macOS / Linux:**
```bash
cd ~/.claude/skills/
git clone https://github.com/IRUJONEU/claude-code-self-distill self-distill
```

**Windows (PowerShell):**
```powershell
cd $env:USERPROFILE\.claude\skills\
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
/self-distill record --positive                              # good experience
/self-distill record --positive --reason "very precise"      # optional reason
/self-distill record --negative                              # frustrating, with corrections
/self-distill record --negative --reason "kept going off track"  # optional reason
```

The reason is written to the archive's frontmatter (`reason` field) and metadata section, making it easier to review during extract. Negative sessions get ×1.5 weight in extract analysis, because correction behavior is the most direct signal for skill needs. Untagged sessions default to neutral.

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

Before generating candidates, the AI applies a **five-question filter**, evaluated in order:

1. **Things Claude already knows** (general programming, standard tool usage, etc.) → discard, no skill needed
2. **One-off needs** (tightly bound to a specific project, won't recur) → discard, not worth solidifying
3. **Behavior preferences** (constraints like "don't add unnecessary comments") → classified as **memory candidate**, listed separately
4. **Should auto-trigger rather than rely on AI judgment** (e.g. "remind me to update PLAN.md after every session") → classified as **hook candidate**, listed separately
5. **Always-active global behavioral rules** (universal, session-independent rules that apply regardless of project — harder rules than memory preferences, like "never auto-push to remote") → classified as **CLAUDE.md candidate**, listed separately

Hook candidate signals: a memory that exists but repeatedly fails to trigger proactively (AI remembers it but never initiates it), or corrections that are about "forgetting to do" rather than "doing it wrong."

#### Incremental tracking and apply-state awareness

Before each extract run, the AI:
1. Compares the existing `_extract_*.md` against current archives and only processes new sessions, reporting: "X total sessions, Y already processed, Z new"
2. Scans current applied state (`~/.claude/skills/`, `~/.claude/memory/`, hooks in `settings.json`) and marks each candidate `[✅ Applied]` / `[❌ Pending]` — so already-completed candidates don't show up as pending again

#### Output format

All candidates that pass the five-question filter are **kept in full**, sorted by demand strength. Four candidate types each get their own section, all with apply-state labels:

```
## Skill Candidate #N: <name> [✅ Applied / ❌ Pending]
- Trigger: when do you repeatedly need this
- Core content: what should this skill tell the AI
- Evidence: which sessions it appeared in (date + topic)
- Demand strength: ★★★☆☆

## Hook Candidate #N: <name> [✅ Applied / ❌ Pending]
- Trigger event: Stop / PostToolUse / SessionStart / ...
- Core behavior: what the hook should do automatically
- Why hook and not memory: ...
- Demand strength: ★★★☆☆

## Memory Candidate #N: <name> [✅ Applied / ❌ Pending]
- Behavior preference: how the AI should treat you
- Demand strength: ★★★☆☆

## CLAUDE.md Candidate #N: <name> [✅ Applied / ❌ Pending]
- Global rule: what always-active constraint this enforces
- Why CLAUDE.md and not memory: session-independent, project-agnostic hard rule
- Demand strength: ★★★☆☆
```

Results are saved to `~/.claude/distill-logs/_extract_YYYY-MM-DD.md`, containing: Skill / Hook / Memory / CLAUDE.md candidate lists, **Analysis Notes** (the AI's reasoning about classification decisions), and structured `applied` / `pending` fields in frontmatter. Multiple runs **merge and update** — historical evidence is never lost.

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
> 1 skill candidate + 1 hook candidate + 5 memory candidates.
> Proceed to \[apply\] to generate SKILL.md / configure hook / write to memory?

### apply — generate skills / configure hooks / update memory

Run after confirming extract results, to turn candidates into actual files.

```
/self-distill apply
```

The AI reads the latest `_extract_*.md`, lists all ❌ Pending candidates, and you choose which ones to apply (enter numbers or "all").

#### Skill generation

The AI uses a built-in process to draft the SKILL.md, and **shows you the content for confirmation before writing any files.**

Generated skills are written to: `~/.claude/skills/<skill-name>/SKILL.md`

#### Hook candidate handling

Patterns identified as "should auto-trigger" in extract are listed separately, with a suggested hook configuration (trigger event + command). You decide whether to write them to `~/.claude/settings.json`:

```
The following patterns are suggested as hooks. Add to settings.json?
- Hook #1: check if PLAN.md needs updating after each session (Stop event)
  command: f=$(find . -maxdepth 3 -name 'PLAN.md' -print -quit 2>/dev/null); ...
```

> ⚠️ Writing hooks requires non-auto mode; if blocked by permissions, the AI will show the JSON for you to paste manually.

#### Memory candidate handling

Patterns identified as "behavior preferences" in extract are listed separately, and you decide whether to write them to memory:

```
The following patterns are better suited for memory than skills.
Add to ~/.claude/memory/?
- Preference #1: don't add a summary paragraph at the end of responses
- Preference #2: code comments should only explain why, not what
```

After confirmation, they are written to `~/.claude/memory/`, where Claude Code will automatically load them in future conversations.

#### CLAUDE.md candidate handling

Patterns identified as "always-active global rules" in extract are listed separately, and you decide whether to append them to `~/.claude/CLAUDE.md`:

```
The following patterns are better suited for CLAUDE.md (hard rules, not preferences).
Append to ~/.claude/CLAUDE.md?
- Rule #1: never auto-push to remote — always wait for explicit user instruction
- Rule #2: don't add Co-Authored-By to commits unless user explicitly requests it
```

After confirmation, they are appended to `~/.claude/CLAUDE.md` as a new section, taking effect in all future sessions across all projects.

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
