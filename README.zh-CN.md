**Language:** [English](README.md) | **简体中文**

# self-distill

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white)

> 你和 AI 的对话习惯是独一无二的。  
> 别人的 skill 模板永远有点不对味，但你自己又不知道从哪开始写。  
> self-distill 帮你从对话里找答案，但由你主导。

一个从你自己的历史对话中发现、提炼并生成个性化 skill 的元工具。

用法很简单：每次对话结束后顺手运行一次 `/self-distill record`，积累够了再在新对话里跑一次 `/self-distill extract`，就够了——这是一个**由你主导**的闭环，最小化对现有工作方式的干扰。

---

## 为什么会有这个工具

这个工具最开始是为了解决我自己的问题而写的。

用 Claude Code 久了之后，我发现自己在反复做同样的事：向 AI 解释同一个约束，纠正同一个方向，补充同一段背景。这些本来都可以写成 skill 一劳永逸——但问题是，我不知道该写什么。

我试过手动整理，但太主观，容易把"我觉得有用"的东西写进去，忽略真正高频的需求。

社区里已经有类似的工具：Hermes skill-factory 可以全自动帮你分析并生成 skill；Claude Code 内置的 `/insights` 也会生成包含摩擦点和行为指标的 HTML 报告。但两者都有同一个问题——**没有筛选机制**。所有对话不加区分地进入分析，低质量 session 里的噪音直接稀释了真正有价值的信号，提炼出来的 skill 也跟着跑偏。

所以 self-distill 的核心原则是：**半自动，主动权在用户。**

你来决定哪些 session 值得存档，AI 来帮你在这些存档里找规律。

---

## 核心特性

- **几乎零 token record**：存档由脚本完成，直接解析 Claude Code 原生的 JSONL 文件，几乎不消耗任何 token，context 用量 95% 时也可安全调用
- **正负例标记**：record 时可标记 `--positive` / `--negative`，负面 session（有纠正行为）在分析时获得更高权重，是最直接的 skill 需求信号
- **三问过滤**：extract 分析前自动过滤掉"Claude 本身已具备的能力"和"一次性需求"，只保留真正值得固化的模式
- **skill + memory 双输出**：行为偏好类候选不强行生成 skill，而是建议写入 memory，由你确认

---

## 这是什么 / 不是什么

| ✅ 是 | ❌ 不是 |
|------|--------|
| 帮你发现你需要什么 skill 或 memory | 帮你写某个具体的 skill（那是 skill-creator） |
| 跨对话的模式挖掘 | 全自动运行，无需干预 |
| 半自动，用户主动筛选 | 只输出 skill |

---

## 工作流程

```
你来筛选              脚本提取              AI 分析
值得存档的 session  →  零 token 存档     →  跨 session 聚合
      ↓                    ↓                    ↓
   [record]            distill-logs/        [extract]
                                                ↓
                                        全量候选列表（按需求强度排序）
                                                ↓
                                           [apply]
                                      ↙            ↘
                               生成 skill      写入 memory
```

三个命令形成闭环，每个环节都可以单独使用。

---

## 安装

### Claude Code

**macOS / Linux：**
```bash
cd ~/.claude/skills/
git clone https://github.com/IRUJONEU/claude-code-self-distill self-distill
```

**Windows（PowerShell）：**
```powershell
cd $env:USERPROFILE\.claude\skills\
git clone https://github.com/IRUJONEU/claude-code-self-distill self-distill
```

Claude Code 会自动发现 `~/.claude/skills/` 下的 skill，无需额外配置。

### Claude.ai（Web）

将 `self-distill/` 目录压缩为 `.zip`，重命名为 `.skill` 后上传至 Settings > Skills。

---

## 依赖

- Python 3.10+（标准库，无需安装额外包）
- Claude Code（record 模式需要访问本地 JSONL 文件）

---

## 用法

### record — 存档当前对话

在一次有价值的对话结束时运行，存档由脚本完成，**几乎零 token 消耗**，任何 context 用量下都可安全调用。

```
/self-distill record
```

AI 会自动推断 topic，运行 `record.py` 脚本解析当前 session 的 JSONL，写入：

```
~/.claude/distill-logs/YYYY-MM-DD_HH-MM_<topic>.md
```

#### 标记对话质量（可选）

```
/self-distill record --positive   # 体验好的对话
/self-distill record --negative   # 体验差、有纠正的对话
```

负面对话在 extract 分析时权重 ×1.5，因为纠正行为是最直接的 skill 需求信号。不标记则默认 neutral。

---

### extract — 蒸馏高频 skill 需求

在积累了一批存档后运行，做跨 session 的模式分析。**建议在新的 session 里运行**，保证有足够的 context 预算。

#### 默认模式

```
/self-distill extract
```

默认模式下：AI 先调用 `extract_users.py` 脚本从所有存档里提取用户发言，得到一份精简文本，再对这份文本做分析——**不读取 assistant 回复，token 消耗较低**。

#### 完整模式

AI 直接读取对话全文（含 assistant 回复），适合存档数量少（< 10 条）或需要捕捉隐性模式时：

```
/self-distill extract --full
```

#### 参数说明

| 参数 | 说明 | 默认 |
|------|------|------|
| `--full` | AI 读全文，含 assistant 回复 | 仅分析用户发言 |
| `--input <路径>` | 额外导入外部对话文件或目录 | 仅读 distill-logs |

#### 冷启动：从历史对话导入

可以通过 `--input` 直接导入已有的历史对话（Claude.ai 导出的 JSON、手动整理的文本等），跳过 record 阶段：

```
/self-distill extract --input ~/Downloads/exported-chats/
/self-distill extract --input ~/Downloads/chat-export.txt
```

#### extract 的分析逻辑

AI 在生成候选前会对每个模式做三问过滤，**以下类型不会进入候选列表**：

1. **Claude 本身已具备的能力**（通用编程、标准工具使用等）→ 不需要 skill
2. **一次性需求**（与特定项目强绑定，完成后不会再出现）→ 不值得固化
3. **行为偏好类**（"不要加超出需求的注释"等约束）→ 更适合写入 memory，单独列出

#### 增量追踪

每次 extract 前，AI 会对比已有的 `_extract_*.md` 和当前存档，只处理新增的 session，并告知：「共 X 条记录，已处理 Y 条，本次新增 Z 条」。从而节约token消耗，且保证历史证据不丢失。

#### 输出格式

所有通过三问过滤的候选**全量保留**，按需求强度排序——没有数量上限，每一个有价值的发现都不会被截断。

```
## Skill 候选 #N: <候选名>
- 触发场景：你在什么情况下反复需要这个
- 核心内容：这个 skill 应该告诉 AI 什么
- 证据来源：出现在哪几个 session（日期 + topic）
- 需求强度：★★★☆☆
```

结果保存至 `~/.claude/distill-logs/_extract_YYYY-MM-DD.md`，包含：Skill 候选、Memory 候选、**Analysis Notes**（AI 的分析推理记录，包括分类边界判断和被过滤模式的原因）。多次运行**合并更新**，历史证据不会丢失。

#### 实际输出示例

以下是基于 17 条真实对话记录运行 extract 的结果：

> **示例 extract 输出** — 蒸馏自 17 条记录
>
> **Skill 候选 #1：会话交接文档化** ★★★★★
> - 触发场景：context 接近上限或到自然交接节点时
> - 核心内容：Claude 应主动将当前状态/已完成/未完成/关键决策/
>   文件位置/下一步写入项目 docs MD，完整到"新开对话能无缝继续"的程度
> - 证据：7/17 sessions（xxx, xxx, xxx, xxx 等）
>
> **Memory 候选**
>
> | # | 模式 | 强度 | 证据 |
> |---|------|------|------|
> | 1 | PLAN.md 持续维护 — 每个阶段完成后主动更新 | ★★★★☆ | 4 sessions |
> | 2 | 危险操作让用户执行 — 给步骤，不直接操作 | ★★★☆☆ | 3 sessions |
> | 3 | 项目启动先建立共识 — 给理解摘要，确认后再读 | ★★★☆☆ | 4 sessions |
> | 4 | 跳过明显确认 — 意图清晰时直接进行 | ★★☆☆☆ | 1 session（主动纠正）|
> | 5 | 始终使用中文 — 不因日志/代码是其他语言切换 | ★★☆☆☆ | 2 sessions（主动纠正）|
>
> 共 1 个 skill 候选 + 5 个 memory 候选。
> 进入 \[apply\] 生成 SKILL.md / 写入 memory 吗？

---

### apply — 生成 skill 或更新 memory

确认 extract 结果后运行，将候选转化为实际文件。

```
/self-distill apply
```

AI 读取最新的 `_extract_*.md`，列出所有候选，你选择要生成哪些（输入编号或"全部"）。

#### skill 生成

如果已安装 [skill-creator](https://github.com/IRUJONEU/claude-code-skill-creator)：AI 自动调用 `/skill-creator`，生成质量更高。

如果未安装：AI 使用内置流程生成，首次会询问是否安装；选择 `never` 可永久跳过提示。

**无论哪种方式，AI 都会先展示内容让你确认，再写入文件。**

生成的 skill 写入：`~/.claude/skills/<skill-name>/SKILL.md`

#### memory 候选处理

extract 中识别为"行为偏好"的模式会单独列出，由你决定是否写入 memory：

```
以下模式更适合写入 memory 而非 skill，是否添加到 ~/.claude/memory/？
- 偏好 #1: 不要在回复末尾加总结段落
- 偏好 #2: 代码注释只写 why，不写 what
```

确认后写入 `~/.claude/memory/`，Claude Code 会在后续对话中自动加载。

---

## 文件结构

```
~/.claude/
├── skills/
│   └── self-distill/
│       ├── SKILL.md
│       ├── scripts/
│       │   ├── record.py           # JSONL → distill log
│       │   └── extract_users.py    # 提取用户发言供 AI 分析
│       └── references/             # 格式规范文档
└── distill-logs/                   # 存档目录（自动创建）
    ├── 2026-04-18_14-30_topic.md   # record 生成
    └── _extract_2026-04-20.md      # extract 生成
```

---

## 设计决策说明

### 为什么 record 用脚本而不是 AI？

两个原因：

1. **context 安全**：对话快结束时往往 context 用量最高，正是最想 record 的时机。如果 record 要消耗 token，高 context 时触发会直接 compact，把刚存的内容也压缩掉。
2. **精确性**：Claude Code 原生把所有对话存为 JSONL，脚本直接解析，用户原文精确到字，不经过 AI 复述，没有偏差。

### 为什么摘要不在 record 阶段生成？

record 只做存档，摘要和分析都推迟到 extract 阶段。这样 record 极限轻量，任何时候都可以安全调用；extract 是用户主动发起的批量操作，有完整的 context 预算，正好做深度分析。

### 为什么是半自动而不是全自动？

对话质量决定分析质量。如果把所有对话都自动纳入分析，水货 session 里的噪音会稀释真正有价值的信号。

你来决定哪些对话值得存档——这不是增加负担，而是质量控制的入口。

---

## License

MIT
