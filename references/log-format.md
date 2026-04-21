# 对话记录格式规范

本文件描述 `record.py` 生成的 distill log 格式，供 Web 环境手动输出时参考。

## 文件命名规则

```
YYYY-MM-DD_HH-MM_<topic>.md
```

示例：
- `2026-04-16_14-30_refactor-auth-flow.md`
- `2026-04-15_09-12_debug-memory-leak.md`
- `2026-04-14_21-05_design-review.md`

topic 命名规则：
- 用连字符连接，小写英文
- 1-4 个词，反映对话核心主题
- 优先用具体词（`cuda-memory-opt`）而非泛化词（`coding-help`）

---

## 文件结构

```markdown
---
date: YYYY-MM-DD HH:MM
topic: <topic>
turns: <对话轮次数>
sentiment: neutral | positive | negative
reason: <标记理由，可选>
tags: []
---

# <topic> — <日期>

## 元信息
- 总轮次：N 轮
- Session 文件：<jsonl-filename>.jsonl
- 标记理由：<理由，仅在提供时出现>

---

## 对话记录

### Turn 1

**User:**
（用户原文，逐字保留，不做任何修改）

**Assistant:**
（assistant 完整原文）

---

### Turn 2

**User:**
（原文）

**Assistant:**
（原文）

---

（以此类推）
```

### 特殊情况

- **skill 调用**：用户消息为 `/skill-name [args]`（已由脚本压缩，原 SKILL.md 注入内容不保留）
- **本地命令**：用户消息为 `[local: /command-name]`（如 `/compact`、`/clear` 等）
- **无 assistant 回复**：`**Assistant:** [无回复]`

---

## sentiment 说明

| 值 | 含义 | extract 权重 |
|----|------|-------------|
| `neutral` | 默认，未标记 | ×1.0 |
| `positive` | 体验好的对话 | ×1.0 |
| `negative` | 有纠正行为的对话 | ×1.5 |

record 时通过 `--positive` / `--negative` flag 设置，默认 `neutral`。可选 `--reason "<理由>"` 附加说明，会写入 frontmatter 的 `reason` 字段（仅在提供时出现）。

---

## tags 建议

常用标签（可扩展）：

任务类型：`debug` `design` `refactor` `research` `explain` `write` `review`

输出类型：`code` `decision` `analysis` `template` `script`

模式标签（用于 extract 分析）：
- `repeat-constraint`：用户反复给出同一约束
- `correction`：用户纠正了 AI 的方向
- `workflow`：涉及固定工作流程
- `style-pref`：涉及写作/回复风格偏好
