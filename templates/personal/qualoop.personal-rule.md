# Qualoop 个人规则（贴一次，所有新项目自动接入）

> 这是用户级 / 个人级 AI 配置片段。粘贴到下面任一位置（按你常用的 AI 工具选），之后所有新项目都会自动接入 Qualoop。

---

## 粘贴位置（按 AI 工具）

| AI 工具 | 粘贴到这里 |
|---------|-----------|
| **Cursor** | `Settings → Rules → User Rules`（或编辑 `~/.cursor/rules/qualoop.mdc`，alwaysApply: true） |
| **Claude Code** | `~/.claude/CLAUDE.md`（macOS/Linux）或 `%USERPROFILE%\.claude\CLAUDE.md`（Windows） |
| **Codex CLI** | `~/.codex/AGENTS.md` |
| **Gemini CLI** | `~/.gemini/GEMINI.md` |
| **Aider** | `~/.aider.conf.yml` 的 `read:` 引用一份本地副本；或者每会话 `/read` |
| **Amp** | 用户级 prompt 设置（参考 Amp 文档） |

> 路径文件若不存在请自行创建（多数工具会自动读取）。

---

## 复制以下全部内容（==== 之间）

====

# Qualoop（质环）个人规则

我习惯用 Qualoop（质环）方法论开发软件。Qualoop 是一套与工具无关的质量闭环：三前提（目标对齐 / 每轮必有产出 / Scorer 打分）+ 五角色（Tester / Scorer / Scheduler / Executor / Guardian）。方法论仓库：<https://github.com/sinogenomics/qualoop>

## 自动触发词（用户对你说以下任一即视为 Qualoop 接入指令）

任一关键词或短语出现都触发：

- 「Qualoop 接入」/「Qualoop 初始化」/「接入 Qualoop」/「按 Qualoop 开发」
- 「质环接入」/「质环初始化」
- 「按 https://github.com/sinogenomics/qualoop.git ... 开发」
- 用户明确给出**开发目标文档路径**（如「开发目标见 docs/GOALS.md」「按目标文档 X 开发」）且当前项目根**不存在 `AGENTS.md`**

## 看到触发词时，按以下顺序执行（不要追问）

1. 抓取并阅读 <https://raw.githubusercontent.com/sinogenomics/qualoop/main/BOOTSTRAP.md>（或在已克隆的 `tools/qualoop/BOOTSTRAP.md` 读它）
2. 严格按 BOOTSTRAP.md 第 1 节 Step 1–6 执行：
   - `git init`（如未初始化）
   - `git submodule add https://github.com/sinogenomics/qualoop.git tools/qualoop`
   - 按平台调用 `tools/qualoop/scripts/install-agents.{ps1|sh}`
     - 用户给了目标文档路径 → `-NorthStarFile <path>` 或 `--north-star-file <path>`
     - 用户给了一句话目标 → `-NorthStar "<text>"` 或 `--north-star "<text>"`
     - 都没给 → 用占位安装，安装后提示用户补 North Star
   - 校验业务项目根出现 `AGENTS.md`、`CLAUDE.md`、`GEMINI.md`、`qualoop.json`
   - `git add -A` 然后 `git commit -m "Add Qualoop AI contract and submodule"`
3. 切换到「Qualoop 契约模式」：从此遵守业务项目根 `AGENTS.md`（三前提、五角色、L1 边界）
4. 紧接着跑**首轮检查**，输出 `automation/issues.json` 与 `automation/reports/latest_issues.md`，向我汇报当轮 `value_qualified` 合格意见数；为 0 → 主动加深检查，**不要回复「没问题」**

## 后续日常触发词

| 我说 | 你做 |
|------|------|
| 「Qualoop 检查」/「质环检查」 | 执行一轮：发现 → Scorer 打分 → ≥1 条 `value_qualified`；更新 issues 与报告 |
| 「Qualoop 加深检查」 | 上轮空轮/低分时扩展 channel，直到有高分合格意见 |
| 「Qualoop 升级到 L2/L3」 | 切 maturity，启用 Scheduler / Executor 链路（仍受三前提约束） |

## 不可违反的不变式

1. 不修改 `tools/qualoop/` 内任何文件（只读 submodule）
2. 不绕过三前提；不删测试 / 不关检测 / 不降阈值换绿
3. L1 默认不大范围自动改业务源码；置信不足 → `requires_human`
4. 每轮必有产出；为 0 视为深度不足，必须加深

====

---

## 之后日常话术（极简版）

| 场景 | 你说 |
|------|------|
| 新项目首次（已有目标文档） | `Qualoop 接入，开发目标见 docs/GOALS.md` |
| 新项目首次（没有目标文档，一句话） | `Qualoop 接入，目标是让 X 在 Y 场景下可靠运行` |
| 每轮质量检查 | `Qualoop 检查` |
| 上轮空轮或低分 | `Qualoop 加深检查` |

URL、submodule 命令、安装脚本路径——**你都不需要再记**。
