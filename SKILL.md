---
name: self-distill
description: >
  Personal conversation distillation system. Records, analyzes, and distills your AI conversations
  to automatically discover and generate personalized skills from your real behavior patterns.
  Contains three sub-commands:
  - /self-distill record: Script directly parses JSONL to archive the current conversation — zero tokens, verbatim accuracy
  - /self-distill extract: Analyzes all archived sessions, identifies high-frequency patterns, outputs full skill candidates sorted by demand strength
  - /self-distill apply: Turns confirmed candidates directly into usable SKILL.md files
  Trigger this skill when the user says:
  "self-distill", "record", "extract", "archive conversation", "save this conversation",
  "distill my skills", "distill history", "analyze my conversations", "analyze my habits",
  "discover what skills I need", "generate my skills", "review past conversations".
  Do NOT trigger when the user is only discussing skill concepts or asking how to write a SKILL.md
  (that is skill-creator's domain).
disable-model-invocation: false
---

# Self-Distill: Personal Conversation Distillation System

## Mode Routing

On invocation, identify the sub-command keyword first:

| User says | Mode |
|-----------|------|
| `record` / `create` / `archive` | → [RECORD MODE] |
| `extract` / `distill` / `analyze` | → [EXTRACT MODE] |
| `apply` / `generate skill` | → [APPLY MODE] |
| No sub-command | → Show help + ask for intent |

---

## Environment Detection

Before executing any mode, determine the current environment:

| Signal | Environment | Behavior |
|--------|-------------|----------|
| bash tool available and `~/.claude/` accessible | **Claude Code** | Read/write local files |
| No bash tool, or user explicitly passes `--output print` | **Web / print mode** | Output structured text directly in conversation |

The user can switch to print mode at any time with `--output print`, or force file mode with `--output file`.

---

## [RECORD MODE]: Archive the current conversation

**Goal**: Precisely archive the complete conversation of the current session, preserving full context.

### Claude Code environment

1. **Determine topic**: Infer from conversation content (1–4 words, hyphen-separated). Use it directly when clear; only ask the user if the topic is ambiguous or has multiple reasonable options.

2. **Run the script** (zero AI involvement, pure script extraction):
   ```bash
   python3 ~/.claude/skills/self-distill/scripts/record.py \
     --project <current project cwd> \
     --topic <topic> \
     [--positive | --negative]  # optional, defaults to neutral
   ```
   Add the corresponding flag when the user explicitly mentions a good or bad experience; omit it otherwise.
   The script automatically: extracts user messages verbatim from JSONL (filtering system tags) + full assistant text, writes to `~/.claude/distill-logs/YYYY-MM-DD_HH-MM_<topic>.md`, and prints the output path.

3. **Inform the user** of the saved path. Done — no AI needs to read any content.

> Summarization and pattern analysis happen in the extract phase. Record only archives.

### Web environment (print mode)

Output the complete session log directly in the conversation, in the same format as the file version (see `references/log-format.md`). The user copies and saves it anywhere (Notion, local file, notes app, etc.).

After output, prompt:
> "This is the complete record of this conversation — copy and save it. Next time you run `/self-distill extract --input <paste content or file path>`, pass it as input to include it in the analysis."

---

## [EXTRACT MODE]: Distill high-frequency skill needs

**Goal**: Read all archived sessions, analyze your behavior patterns, output top-k real skill candidates.

> ⚠️ **Check context state before running**: extract is a cross-conversation meta-analysis, naturally suited to a fresh session.
> If the current conversation has substantial content (noticeable compaction, or many turns), proactively prompt:
> "extract is recommended in a new conversation to ensure sufficient context budget. Continue anyway?"
> Proceed only after the user confirms.

### Parameters

```
/self-distill extract [--input <path>] [--full]
```

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--input <path>` | Read additional external conversation files (txt/md); supports single file or directory | distill-logs only |
| `--full` | AI reads the full conversation (including assistant text) | Script extracts user messages; AI analyzes compact text only |

### Execution steps

1. **Parse parameters**, confirm read scope and depth

2. **Incremental check: determine sessions to process**

   Scan distill-logs, and check whether an old `_extract_*.md` exists:

   ```bash
   ls ~/.claude/distill-logs/*.md | grep -v '_extract_'
   ```

   - If an old `_extract_*.md` exists: read its `processed_sessions` field from frontmatter to get the list of already-processed files
   - Compute **new sessions = all sessions − processed_sessions**
   - Report to user: "X total sessions, Y already processed, Z new."

   If new sessions = 0, prompt: "All sessions have been processed in the last extract. Re-run full analysis?" Wait for confirmation before continuing.

3. **Single script call to generate all batch files**

   Default mode (without `--full`) — **single script call**, script handles splitting:
   ```bash
   python3 ~/.claude/skills/self-distill/scripts/extract_users.py \
     ~/.claude/distill-logs/ \
     --files <new session filenames> \
     --batch-size 5 \
     --output-dir ~/.claude/distill-logs/_extract_batches
   ```
   Script automatically: truncates long messages (default 500 chars), splits M files into ceil(M/5) batch files, outputs each file path.

   Full mode (`--full`): AI reads the files' complete content directly, skipping the script.

   **Analysis phase (read batch files serially)**

   Use the old `_extract_` candidate list as the initial **running base** (empty if no old file):

   ```
   For each batch file generated by the script (_batch_001.txt, _batch_002.txt, ...):
     1. Read the batch file
     2. AI analyzes: batch content + current running base candidate list
        → merge duplicates, strengthen existing evidence, append new patterns, filter noise
     3. Update running base = merged result from this batch
   After all batches, running base = final candidate list
   ```

   > Report progress to user during analysis: "Processing batch N/M…"
   > Clean up batch files after analysis: `rm -rf ~/.claude/distill-logs/_extract_batches`

4. **Aggregate and group (merge similar items)**
   - Merge semantically similar patterns
   - Count **frequency** and **cross-session occurrence rate** for each pattern
   - Correction behavior in negative sessions gets weight ×1.5 (from frontmatter `sentiment: negative`)
   - Calculate **demand strength = frequency × cross-session rate**

4.5. **Candidate quality filter (three-question check)**

   For each aggregated pattern, ask three questions in order. If any answer is "yes", the pattern does not become a skill candidate:

   | Question | Criterion | Action |
   |----------|-----------|--------|
   | Can Claude do this well without a skill? | Claude already has this domain knowledge (general programming, standard tools, common workflows) | Discard |
   | Is this a one-off need? | Tightly bound to a specific current project, will not recur after completion | Discard |
   | Better suited for memory/preferences? | Not a workflow, but a behavioral preference about "how the AI should treat you" | Classify as **memory candidate** |

   Memory candidates do not generate skills. They are listed separately after step 7, and the user decides in the apply phase whether to write them to memory.

5. **Generate full candidate list (sorted by demand strength)**

   Keep all candidates that pass the three-question filter, no truncation. Sort by demand strength descending:
   ```
   ## Skill Candidate #N: <name>
   - Trigger: when do you repeatedly need this
   - Core content: what should this skill tell the AI
   - Evidence: which sessions it appeared in (date + topic)
   - Demand strength: ★★★☆☆ (frequency / session count)
   ```
   Memory candidates are also kept in full, listed in a separate section, also sorted by demand strength.

6. **Save / output results**

   **Claude Code environment**: write to file
   ```
   ~/.claude/distill-logs/_extract_<YYYY-MM-DD>.md
   ```
   File structure:
   - frontmatter: update `processed_sessions` (complete list)
   - **Analysis Notes section**: record key AI reasoning from this run — why certain patterns were classified as skill vs memory vs discarded, cross-batch observations, notable boundary judgments. This is the core of the distillation record, referenced by future extract runs.
   - Skill candidates full list (sorted by demand strength)
   - Memory candidates full list (sorted by demand strength)
   - Filter explanation (discarded patterns and reasons)
   - Merge history (changes when merging with old `_extract_`)

   When merging with old file: strengthen existing evidence, append new candidates, re-sort by demand strength, preserve full history.

   **Web environment**: output the complete extract report directly in the conversation (format: `references/extract-format.md`).
   Prompt the user to copy and save it. Pass the old report via `--input` next time for incremental accumulation.

7. **Ask the user**:
   > "These are the full candidates distilled from X archived sessions (N skills, M memory). Would you like to edit a candidate's description, or proceed to [apply] to generate SKILL.md files? Memory candidates can also be confirmed for writing in the apply phase."

---

## [APPLY MODE]: Generate usable SKILL.md files

**Goal**: Turn confirmed skill candidates into properly formatted `SKILL.md` files.

### Execution steps

1. **Retrieve extract results**

   **Claude Code environment**: read the latest local extract file
   ```
   ~/.claude/distill-logs/_extract_<latest date>.md
   ```
   **Web environment**: use the candidate list from this conversation's extract output, or ask the user to paste a previously saved extract report

2. **Confirm which skills to generate**
   - If the user hasn't specified, list all candidates and ask them to choose (enter numbers or "all")
   - If the extract results contain **memory candidates**, list them separately and ask:
     > "The following patterns are better suited for memory than skills. Add to `~/.claude/memory/`?"
     > [List memory candidates; write after user confirms]

3. **Generate SKILL.md for each candidate**

   Check skill_creator availability, decide by priority:

   ```
   ~/.claude/skills/skill-creator/ exists?
     Yes → call /skill-creator, pass candidate description (trigger + core content) as input
     No  → read skill_creator field from ~/.claude/skills/self-distill/config.json
           "skip"    → use built-in process directly, no further prompts
           not set   → ask the user (see below)
   ```

   **First-time prompt when skill_creator is not detected**:
   > "skill-creator not found. It can significantly improve generation quality.
   > Choose:
   > - `y` — install now (installation steps will be shown)
   > - `n` — skip for this session, use built-in process
   > - `never` — skip and never prompt again (writes to config)"

   - `y`: show installation steps; re-trigger apply after user installs
   - `n`: use built-in process this time; will ask again next time
   - `never`: write to `~/.claude/skills/self-distill/config.json` (`{"skill_creator": "skip"}`), use built-in process

   **Built-in process (fallback)**:
   - Follow standard frontmatter format (name, description)
   - description should be "proactive" — include trigger keyword phrases to prevent under-triggering
   - Draft body from candidate content; keep concise (<100 lines)

   **Either way, always show content for user confirmation or editing before writing/outputting**

4. **Write or output**

   **Claude Code environment**: write to `~/.claude/skills/<skill-name>/SKILL.md`; Claude Code discovers it automatically.

   **Web environment**: output the complete SKILL.md text (including frontmatter) for each skill in the conversation. After copying, the user should:
   - Create a local folder `<skill-name>/` and save the content as `SKILL.md`
   - Compress as ZIP → upload to Claude.ai Settings > Skills

---

## Additional commands

### `/self-distill status`
Shows:
- Number of archived sessions and time span
- Date and top-k summary of the latest extract file
- List of generated skills

### `/self-distill package <skill-name>`
Packages the specified skill directory as a `.skill` file for Claude.ai upload.
See `references/packaging.md`.

### Cold start: bootstrap extract from existing history

If distill-logs has no accumulated archives yet, feed existing conversations directly to extract:

```
/self-distill extract --input ~/Downloads/exported-chats/
/self-distill extract --input ~/Downloads/chat-export.txt
```

External file format is unrestricted — treated as plain text. Claude.ai supports exporting conversation history from the settings page.
This way, the first extract is not empty — you can work directly from all your existing history.

---

## Core principles

1. **Accuracy first**: record is done by script; user text is taken directly from JSONL, not paraphrased by AI — no drift allowed
2. **Incremental updates**: extract merges rather than overwrites; historical evidence is never lost
3. **User confirmation**: the user must confirm skill content before apply writes anything — no silent generation
4. **Path consistency**: all files stored in `~/.claude/distill-logs/`; skills output to `~/.claude/skills/`
5. **Context awareness**: extract is a cross-conversation meta-operation; proactively check context state before starting, suggest a new session if needed
