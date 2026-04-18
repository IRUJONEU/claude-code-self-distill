# Extract Output File Format

## File Naming

```
_extract_YYYY-MM-DD.md
```

Each extract run generates a new version, merged with the previous one (historical evidence is never lost).

---

## File Structure

```markdown
---
generated: YYYY-MM-DD
sessions_analyzed: N
date_range: YYYY-MM-DD to YYYY-MM-DD
previous_extract: _extract_YYYY-MM-DD.md (if any)
processed_sessions:
  - 2026-04-18_07-04_self-distill-release-prep.md
  - 2026-04-17_12-30_other-topic.md
---

# Self-Distill Extract Report

## Overview

- Sessions analyzed: N (X negative, weighted ×1.5)
- Time span: X days
- New sessions since last extract: P
- Skill candidates: N, Memory candidates: M, Filtered/discarded: K

---

## Analysis Notes

Key reasoning from this run, for reference in future extract runs:

- **Cross-batch observations**: (e.g., ROS debugging pattern in batches 1-2 and Docker pattern in batch 3 are essentially the same "tool config" type — merged and filtered as domain knowledge)
- **Boundary judgments**: (e.g., session handoff documentation vs PLAN.md maintenance — former is a workflow with a clear trigger, latter is a continuous habit preference, so former → skill, latter → memory)
- **Notable signals**: (e.g., "let user execute risky ops" appeared as correction behavior in 3 sessions — low frequency but high confidence)
- **Other observations**: (reasoning about filtered patterns, and a brief description of overall behavioral profile)

---

## Skill Candidates (full, sorted by demand strength)

---

### Skill Candidate #1: <name>

**Demand strength**: ★★★★☆ (frequency: X times, across N sessions)

**Trigger**:
When do you repeatedly need this — describe with concrete scenarios, not abstract terms.

**Core content**:
What should this skill tell the AI — specific constraints, preferences, workflow steps.

**Evidence**:
| Session | Date | Specific instance |
|---------|------|-------------------|
| topic-a | 2026-04-12 | User required all code comments to explain why, not what |
| topic-b | 2026-04-10 | User corrected "don't use .cuda(), use .to(device)" |
| topic-c | 2026-04-08 | Same preference recurred (negative session, weight bonus) |

**Draft skill description** (for use in apply phase):
> When the user is working on [domain] tasks, follow these constraints: [specific rule list]

---

### Skill Candidate #2: <name>

(same format as above, and so on — list all skill candidates that passed the three-question filter in full)

---

## Memory Candidates (full, sorted by demand strength)

The following patterns were classified as "behavior preferences / interaction constraints" by the three-question filter — better suited for memory than skills.

---

### Memory Candidate #1: <description>

- **Demand strength**: ★★★★☆
- **Pattern**: specific description of this behavioral preference
- **Typical phrasing**: "..." (user's own words)
- **Evidence**: topic-a, topic-b (X sessions)
- **Classification reason**: why this is memory rather than skill

---

(and so on — list all memory candidates in full)

---

## Discarded Patterns (filtered by three-question check)

| Pattern | Filter reason | Note |
|---------|---------------|------|
| Docker Compose usage | Domain knowledge Claude already has | No skill needed |
| Directory structure of a specific project | One-off need | Won't be reused after project ends |

---

## Merge History

(Recorded when this extract merged a previous version)

- Candidate #1 demand strength increased from ★★★ to ★★★★ (2 new evidence items)
- Candidate #3 is new this run (from 2 new sessions)
- Former candidate #4 demoted to discarded/filtered (single session only, not seen recently)
```

---

## Analysis Dimensions Reference

During the extract phase, classify signals along these dimensions:

### Skill candidate signals (high-frequency, cross-session, reusable)

**1. Recurring user constraints**
- "never add XX", "always add XX"
- Specific naming conventions, code style rules
- "be concise", "no filler"

**2. Repeated corrections to the AI**
- "that's not what I meant" (signals a systematic AI misunderstanding)
- "do it a different way" (signals a fixed preference the AI hasn't internalized)
- Correction behavior in negative sessions, weight ×1.5

**3. Fixed workflows**
- Steps for a certain type of task are consistently the same
- User repeatedly guides the AI through the same sequence

### Memory candidate signals (behavior preferences / interaction constraints)

**4. Preferences about how the AI responds**
- Tone, format, whether to add summary paragraphs
- Boundary between exploratory questions vs. direct execution
- Response length preference

### Three-question filter (the following types do not become skill candidates)

| Question | Criterion | Action |
|----------|-----------|--------|
| Can Claude do this well without a skill? | General programming ability, standard tool usage, domain knowledge | Discard |
| Is this a one-off need? | Tightly bound to a specific project, will not recur | Discard |
| Better suited for memory/preferences? | Not a workflow, but "how the AI should treat you" | → Memory candidate |
