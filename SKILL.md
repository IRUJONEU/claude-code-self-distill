---
name: self-distill
description: >
  个人对话蒸馏系统。用于记录、分析和提炼你与 AI 的对话，从你真实的行为模式中自动发现并生成个性化 skill。
  包含三个子命令：
  - /self-distill record（记录）：脚本直接解析 JSONL 存档当前对话，零 token，精确到字
  - /self-distill extract（提炼）：分析所有历史记录，统计高频模式，输出 top-k skill 候选
  - /self-distill apply（应用）：将认可的 skill 候选直接生成可用的 SKILL.md 文件
  当用户说以下内容时，务必调用此 skill：
  "self-distill"、"record"、"extract"、"记录对话"、"存档对话"、"保存这次对话"、
  "蒸馏我的 skill"、"提炼历史"、"提炼对话"、"分析我的对话"、"分析我的习惯"、
  "发现我需要什么 skill"、"生成我的 skill"、"整理过去的对话"。
  不要在用户只是讨论 skill 概念、或询问如何写 SKILL.md 时触发（那是 skill-creator 的范围）。
disable-model-invocation: false
---

# Self-Distill：个人对话蒸馏系统

## 模式路由

用户调用时，先识别子命令关键词：

| 用户说 | 执行模式 |
|--------|---------|
| `record` / `create` / `记录` / `存档` | → [RECORD 模式] |
| `extract` / `提炼` / `蒸馏` / `分析` | → [EXTRACT 模式] |
| `apply` / `应用` / `生成 skill` | → [APPLY 模式] |
| 无子命令 | → 展示帮助 + 询问意图 |

---

## 环境检测

在执行任何模式前，先判断当前运行环境：

| 判断依据 | 环境 | 行为 |
|---------|------|------|
| bash 工具可用，且能访问 `~/.claude/` | **Claude Code** | 读写本地文件 |
| 无 bash 工具，或用户显式传入 `--output print` | **Web / 输出模式** | 直接在对话中输出结构化文本 |

用户也可以随时用 `--output print` 强制切换到输出模式，或用 `--output file` 强制写文件模式。

---

## [RECORD 模式]：记录当前对话

**目标**：将当前 session 的完整对话精确存档，避免语境缺失。

### Claude Code 环境

1. **确定 topic**：根据对话内容推断（1-4 个词，连字符连接）。topic 明确具体时直接使用，无需确认；只在 topic 模糊或有多个合理选项时才询问用户。

2. **运行脚本**（零 AI 介入，纯脚本提取）：
   ```bash
   python3 ~/.claude/skills/self-distill/scripts/record.py \
     --project <当前项目的 cwd> \
     --topic <topic> \
     [--positive | --negative]  # 可选，默认 neutral
     [--reason "<理由>"]        # 可选，附加标记理由
   ```
   用户主动提到体验好或体验差时，自动加对应 flag；若用户给出了理由（如"回复很精准"、"多次跑偏"），用 `--reason` 传入；未提及则省略。
   脚本自动：从 JSONL 精确提取用户原文（过滤系统标签）+ assistant 原文，写入 `~/.claude/distill-logs/YYYY-MM-DD_HH-MM_<topic>.md`，输出文件路径。

3. **告知用户**保存路径，完成。无需 AI 读取任何内容。

> 摘要和模式分析在 extract 阶段完成，record 只做存档。

### Web 环境（输出模式）

直接在对话中输出完整的 session 记录文本，格式与文件版完全一致（见 `references/log-format.md`），用户自行复制保存到任意位置（Notion、本地文件、备忘录等）。

输出完成后提示：
> "以上是本次对话的完整记录，可以复制保存。下次运行 `/self-distill extract --input <粘贴内容或文件路径>` 时将其作为输入即可纳入分析。"

---

## [EXTRACT 模式]：蒸馏高频 skill 需求

**目标**：读取所有历史记录，分析你的行为模式，输出 top-k 个真实 skill 候选。

> ⚠️ **执行前先检查 context 状态**：extract 是跨对话的元分析，天然适合在全新 session 里运行。
> 如果当前对话已经进行了相当内容（明显有过 compact，或对话轮次较多），应主动提示：
> "extract 建议在新的对话中运行，以保证分析有充足的 context 预算。是否继续？"
> 用户确认后再执行。

### 参数说明

```
/self-distill extract [--input <路径>] [--full]
```

| 参数 | 说明 | 默认行为 |
|------|------|---------|
| `--input <路径>` | 额外读取外部对话文件（txt/md），支持单文件或目录 | 仅读取 distill-logs |
| `--full` | AI 读取完整对话（含 assistant 原文） | 脚本提取用户发言，AI 只分析精简文本 |

### 执行步骤

1. **解析参数**，确认读取范围和深度

2. **增量检查：确定需要处理的 session**

   扫描 distill-logs，同时检查是否存在旧的 `_extract_*.md`：

   ```bash
   ls ~/.claude/distill-logs/*.md | grep -v '_extract_'
   ```

   - 如果存在旧 `_extract_*.md`：读取其 frontmatter 中的 `processed_sessions` 字段，得到已处理文件列表
   - 计算 **新 session = 全部 session − processed_sessions**
   - 告知用户：「共 X 条记录，已处理 Y 条，本次新增 Z 条」

   若新 session = 0，提示用户：「所有记录已在上次提炼中处理。是否重新全量分析？」，等待确认后再继续。

3. **一次调用脚本，生成所有 batch 文件**

   默认模式（不带 `--full`）——**单次脚本调用**，脚本负责切分：
   ```bash
   python3 ~/.claude/skills/self-distill/scripts/extract_users.py \
     ~/.claude/distill-logs/ \
     --files <新 session 文件名列表> \
     --batch-size 5 \
     --output-dir ~/.claude/distill-logs/_extract_batches
   ```
   脚本自动：截断超长消息（默认 500 字符），将 M 个文件切分为 ceil(M/5) 个 batch 文件，输出各文件路径。

   完整模式（`--full`）：AI 直接读取这几个文件的完整内容，跳过脚本。

   **分析阶段（串行读取 batch 文件）**

   以旧 `_extract_` 的候选列表作为初始 **running base**（如无旧文件则从空开始）：

   ```
   对脚本生成的每个 batch 文件（_batch_001.txt, _batch_002.txt, ...）：
     1. 读取该 batch 文件
     2. AI 分析：batch 内容 + 当前 running base 候选列表
        → 合并同类项，强化已有证据，新增新模式，过滤噪音
     3. 更新 running base = 本批合并结果
   所有批次完成后，running base = 最终候选列表
   ```

   > 分析过程中向用户报告进度：「正在处理第 N/M 批…」
   > 分析完成后清理 batch 文件：`rm -rf ~/.claude/distill-logs/_extract_batches`

4. **聚合归类（合并同类项）**
   - 将语义相近的模式合并
   - 统计每个模式出现的**频次**和**跨 session 出现率**
   - negative session 中的纠正行为权重 ×1.5（来自 frontmatter `sentiment: negative`）
   - 计算**需求强度 = 频次 × 跨 session 率**

4.5. **候选质量过滤（三问判断）**

   对每个聚合后的模式，依次问三个问题，任何一个为"是"则不进入 skill 候选：

   | 问题 | 判断标准 | 处理 |
   |------|---------|------|
   | 不需要 skill 也能做好？ | Claude 本身已具备此领域知识（通用编程、工具使用、标准流程） | 丢弃 |
   | 一次性需求？ | 与当前特定项目强绑定，完成后不会复现 | 丢弃 |
   | 更符合 memory/偏好？ | 不是流程，而是"AI 应该如何对待你"的行为偏好或约束 | 分类为 **memory 候选** |

   memory 候选不生成 skill，在步骤 7 后单独列出，apply 阶段由用户决定是否写入 memory。

5. **生成全量候选列表（按需求强度排序）**

   保留所有通过三问过滤的候选，不截断。按需求强度降序排列：
   ```
   ## Skill 候选 #N: <候选名>
   - 触发场景：你在什么情况下反复需要这个
   - 核心内容：这个 skill 应该告诉 AI 什么
   - 证据来源：出现在哪几个 session（日期 + topic）
   - 需求强度：★★★☆☆（频次 / 跨 session 数）
   ```
   Memory 候选同样全量保留，单独成节，同样按需求强度排序。

6. **保存/输出提炼结果**

   **Claude Code 环境**：写入文件
   ```
   ~/.claude/distill-logs/_extract_<YYYY-MM-DD>.md
   ```
   文件结构：
   - frontmatter：更新 `processed_sessions`（完整列表）
   - **Analysis Notes 节**：记录 AI 在本次分析中的关键推理——为什么某些模式被归为 skill vs memory vs 丢弃，跨 batch 观察到的规律，值得注意的边界判断。这是蒸馏记录的核心，供后续 extract 参考。
   - Skill 候选全量列表（按需求强度排序）
   - Memory 候选全量列表（按需求强度排序）
   - 过滤说明（被丢弃的模式及原因）
   - 历史合并记录（如有旧 `_extract_` 合并时的变化）

   候选列表合并旧文件时：强化已有证据，新增新候选，重新按需求强度排序，保留完整历史。

   **Web 环境**：直接在对话中输出完整提炼报告（格式见 `references/extract-format.md`），
   提示用户复制保存。下次 extract 时可通过 `--input` 传入旧报告，实现增量累积。

7. **询问用户**：
   > "以上是从 X 条对话记录中蒸馏出的全量候选（N 个 skill，M 个 memory）。你想修改某个候选的描述，还是直接进入 [apply] 生成 SKILL.md？Memory 候选也可以在 apply 阶段确认写入。"

---

## [APPLY 模式]：生成可用的 SKILL.md

**目标**：将用户认可的 skill 候选，直接生成标准格式的 `SKILL.md` 文件。

### 执行步骤

1. **获取提炼结果**

   **Claude Code 环境**：读取本地最新提炼文件
   ```
   ~/.claude/distill-logs/_extract_<最新日期>.md
   ```
   **Web 环境**：使用本次对话中 extract 输出的候选列表，或请用户粘贴之前保存的提炼报告

2. **确认要生成哪些 skill**
   - 如果用户没有指定，列出所有候选，请用户选择（输入编号或 "全部"）
   - 如果提炼结果中有 **memory 候选**，单独列出并询问：
     > "以下模式更适合写入 memory 而非 skill，是否添加到 `~/.claude/memory/`？"
     > [列出 memory 候选，用户确认后写入]

3. **生成每个候选的 SKILL.md**

   检查 skill_creator 可用性，按以下优先级决策：

   ```
   ~/.claude/skills/skill-creator/ 存在？
     是 → 调用 /skill-creator，把候选描述（触发场景 + 核心内容）作为输入
     否 → 读取 ~/.claude/skills/self-distill/config.json 中的 skill_creator 字段
           "skip"  → 直接走内置流程，不再询问
           未设置  → 询问用户（见下）
   ```

   **首次未检测到 skill_creator 时的询问**：
   > "未检测到 skill-creator。它可以显著提升生成质量。
   > 请选择：
   > - `y` — 现在安装（将显示安装方式）
   > - `n` — 本次跳过，使用内置流程
   > - `never` — 跳过，且以后不再提示（写入配置）"

   - `y`：提示安装步骤，用户安装后重新触发 apply
   - `n`：本次走内置流程，下次仍会询问
   - `never`：写入 `~/.claude/skills/self-distill/config.json`（`{"skill_creator": "skip"}`），走内置流程

   **内置流程（fallback）**：
   - 遵循标准 frontmatter 格式（name、description）
   - description 要"有点主动"——包含触发场景关键词，防止欠触发
   - body 根据候选内容起草，保持简洁（<100 行）

   **无论哪种方式，都先展示内容让用户确认或修改，再执行写入/输出**

4. **写入或输出**

   **Claude Code 环境**：写入 `~/.claude/skills/<skill-name>/SKILL.md`，Claude Code 自动发现。

   **Web 环境**：在对话中直接输出每个 SKILL.md 的完整文本（含 frontmatter）。用户复制后：
   - 本地新建文件夹 `<skill-name>/`，将内容存为 `SKILL.md`
   - 压缩为 ZIP → 上传到 Claude.ai Settings > Skills
---

## 附加命令

### `/self-distill status`
显示：
- 已记录的对话数量和时间跨度
- 最新提炼文件的日期和 top-k 列表摘要
- 已生成的 skill 列表

### `/self-distill package <skill-name>`
将指定 skill 目录打包为 `.skill` 文件，用于 Claude.ai 上传。
参考 `references/packaging.md`。

### 冷启动：用历史对话热启动 extract

如果 distill-logs 还没有积累，可以把已有的历史对话直接喂给 extract：

```
/self-distill extract --input ~/Downloads/exported-chats/
/self-distill extract --input ~/Downloads/chat-export.txt
```

外部文件格式不限，按纯文本处理。Claude.ai 支持从设置页面导出对话记录。
这样第一次 extract 就不是空的，可以直接基于已有所有历史对话工作。

---

## 重要原则

1. **精确优先**：record 由脚本完成，用户原文直接从 JSONL 取，不经过 AI，不能有偏差
2. **增量更新**：extract 不覆盖旧结果，而是合并，历史证据不丢失
3. **用户确认**：apply 前必须让用户确认 skill 内容，不静默生成
4. **路径一致性**：所有文件统一存储在 `~/.claude/distill-logs/`，skill 输出到 `~/.claude/skills/`
5. **context 自觉**：extract 是跨对话的元操作，进入前主动检查 context 状态，必要时建议新开对话
