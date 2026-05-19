# 一句话接入 Qualoop（任何 AI 工具适用）

把下面这句话对你的 AI（Codex CLI / Cursor / Claude Code / Gemini CLI / Aider / Amp 等）说一次：

```
针对本项目的开发目标（见 docs/GOALS.md），按 https://github.com/sinogenomics/qualoop.git
的 BOOTSTRAP.md 接入到 tools/qualoop，然后用 Qualoop 方法论完成开发。
```

**替换前请确认**：

- `docs/GOALS.md` → 改成你项目实际的目标文档路径（绝对路径也行，安装脚本会自动复制）
- 业务项目目录 = 你执行 AI 命令时的工作目录
- 业务项目最好已经 `git init`（不然 AI 会先帮你跑）

**没有目标文档怎么办**（用一句话代替）：

```
针对本项目的开发目标（"用一句话写在这里：例如 让 X 在 Y 场景下可靠运行"），
按 https://github.com/sinogenomics/qualoop.git 的 BOOTSTRAP.md 接入到 tools/qualoop，
然后用 Qualoop 方法论完成开发。
```

**完成首次接入后，日常只说**：

```
Qualoop 检查
```
