# Skill 打包说明

## Claude Code 环境

在 Claude Code 中，skill 目录放在 `~/.claude/skills/` 下即可自动发现，无需打包。

```bash
# 验证 skill 已被识别
claude --list-skills
```

## Claude.ai 环境（上传 .skill 文件）

`.skill` 文件本质上是一个 zip 压缩包，重命名后缀为 `.skill`。

### 打包步骤

```bash
# 打包指定 skill
cd ~/.claude/skills/
zip -r <skill-name>.skill <skill-name>/
mv <skill-name>.zip <skill-name>.skill
```

或使用以下脚本（在 skill 目录下运行）：

```bash
#!/bin/bash
SKILL_NAME=$1
if [ -z "$SKILL_NAME" ]; then
  echo "用法: package_skill.sh <skill-name>"
  exit 1
fi

cd ~/.claude/skills/
zip -r "${SKILL_NAME}.skill" "${SKILL_NAME}/"
echo "已生成: ~/.claude/skills/${SKILL_NAME}.skill"
```

### 上传到 Claude.ai

1. 打开 Claude.ai
2. 进入 Settings（设置）> Skills（技能）
3. 点击 "Upload Skill"
4. 选择 `.skill` 文件
5. 上传后在对话中即可使用

---

## 批量打包所有 self-distill 生成的 skill

```bash
cd ~/.claude/skills/
for dir in */; do
  skill_name="${dir%/}"
  zip -r "${skill_name}.skill" "${dir}"
  echo "已打包: ${skill_name}.skill"
done
```
