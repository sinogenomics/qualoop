# Qualoop 个人规则（贴一次，所有新项目自动接入）

> 这是用户级 / 个人级 AI 配置片段。粘贴到下面任一位置（按你常用的 AI 工具选），之后所有新项目都会自动接入 Qualoop。
> 推荐用一句话脚本安装：见 [`../../scripts/install-personal-rule.sh`](../../scripts/install-personal-rule.sh) / `.ps1`。

---

## 粘贴位置（按 AI 工具）

| AI 工具 | 粘贴到这里 |
|---------|-----------|
| **Cursor** | `Settings → Rules → User Rules`（或编辑 `~/.cursor/rules/qualoop.mdc`，`alwaysApply: true`） |
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

## 自动触发条件（满足以下任一即视为 Qualoop 接入指令）

1. 消息中包含触发词：「Qualoop 接入」/「Qualoop 初始化」/「接入 Qualoop」/「按 Qualoop 开发」/「质环接入」
2. 消息中**同时**出现 Qualoop 仓库链接（`github.com/sinogenomics/qualoop` 或它的 raw 子域）**和**任何描述项目需求的内容（路径或一句话）
3. 用户明确给出**开发目标文档路径**（如「开发目标见 docs/GOALS.md」「按目标文档 X 开发」）且当前项目根**不存在 `AGENTS.md`**

## STEP 0：解析用户输入（识别需求来源）

用户在新项目首条消息里通常只给两件事：Qualoop 仓库链接 + 项目需求。需求有两种形态：

- **(A) 文件路径**：`docs/GOALS.md`、`需求.md`、`requirements.txt` 等
- **(B) 一句话**：「让 X 在 Y 场景下可靠运行」

识别规则（顺序执行）：

1. 把 Qualoop URL 从消息里挑出去
2. 剩余文本里找候选路径：含 `/` 或 `\` 的 token、`.md`/`.txt`/`.rst`/`.pdf`/`.docx`/`.json` 结尾、「见 X」「需求文档 X」「目标见 X」「per X」之后的字符串
3. 候选路径用 `test -f` / `Test-Path` 验证存在 → 模式 (A)，传 `--north-star-file <path>` / `-NorthStarFile <path>`
4. 候选路径不存在 → 一次性问用户确认，并列出最相似的 `*GOAL*` / `*目标*` / `*需求*` / `*PRD*` / `*REQUIREMENT*` 候选
5. 零路径候选 → 剩余自然语言整段作为一句话目标，传 `--north-star "<text>"` / `-NorthStar "<text>"`
6. 多个候选 → 按文件名 `(?i)GOAL|目标|需求|REQUIREMENT|PRD|SPEC` 优先；仍歧义则问一次

不要反复追问；能从消息直接推断的就直接做。

## STEP 1：执行接入（不要追问，按顺序）

1. 抓取并阅读 <https://raw.githubusercontent.com/sinogenomics/qualoop/main/AI-START-HERE.md>，按它的全部 STEP（含本规则覆盖的 STEP 0/1）执行
2. 关键命令（在业务项目根，不在 qualoop 仓库根）：
   - `git init`（如未初始化）
   - `git submodule add https://github.com/sinogenomics/qualoop.git tools/qualoop`
   - 按 STEP 0 结果调用 `tools/qualoop/scripts/install-agents.{ps1|sh}` 并传入 `--north-star-file` 或 `--north-star`
   - 校验业务项目根出现 `AGENTS.md`、`CLAUDE.md`、`GEMINI.md`、`qualoop.json`
   - `git add -A && git commit -m "Add Qualoop AI contract and submodule"`
3. 进入 Qualoop 契约模式（读业务项目根 `AGENTS.md`，默认 `maturity = L1`）
4. 立刻跑首轮检查，写 `automation/issues.json` 与 `automation/reports/latest_issues.md`

## STEP 2：向用户输出 Qualoop 简报（必做，不要省略）

接入成功后**主动向用户输出**以下内容（用用户的语言；中文用户输出中文）：

> ✅ Qualoop 已接入本项目（成熟度 L1）。
>
> **北极星**：<这里写解析到的 North Star（文件路径或一句话）>
>
> **生成的文件**：AGENTS.md / CLAUDE.md / GEMINI.md / qualoop.json / tools/qualoop/（只读 submodule）/ automation/
>
> **第一轮检查**：合格意见 N 条（最高分 X）。报告：`automation/reports/latest_issues.md`
>
> **从现在起你只需要说**：
> - `Qualoop 检查` — 跑下一轮
> - `Qualoop 加深检查` — 上轮低分时扩展渠道
> - `Qualoop 升级到 L2` / `L3` — 启用 Scheduler / Executor
> - 任何自然语言开发请求 — 我都在 Qualoop 契约下执行
>
> **三前提（我永远不会违反）**：目标对齐 / 每轮必有产出 / Scorer 打分 ≥ 60

这是用户对 Qualoop 仪式感的唯一一次接触点，**务必完整输出**。

## 后续日常触发词

| 我说 | 你做 |
|------|------|
| 「Qualoop 检查」/「质环检查」 | 跑一轮：发现 → Scorer 打分 → ≥1 条 `value_qualified` |
| 「Qualoop 加深检查」 | 上轮空轮/低分时扩展 channel，直到有高分合格意见 |
| 「Qualoop 升级到 L2/L3」 | 切 maturity，启用 Scheduler / Executor 链路 |

## 不可违反的不变式

1. 不修改 `tools/qualoop/` 内任何文件（只读 submodule）
2. 不绕过三前提；不删测试 / 不关检测 / 不降阈值换绿
3. L1 默认不大范围自动改业务源码；置信不足 → `requires_human`
4. 每轮必有产出；为 0 视为深度不足，必须加深

====

---

## 配置完之后的极简话术

| 场景 | 你说 |
|------|------|
| 新项目首次（有需求文档） | `<github repo URL> + docs/GOALS.md` 或 `Qualoop 接入，开发目标见 docs/GOALS.md` |
| 新项目首次（一句话需求） | `<github repo URL> + 让 X 在 Y 场景可靠运行` |
| 每轮质量检查 | `Qualoop 检查` |
| 上轮空轮或低分 | `Qualoop 加深检查` |

**URL、submodule 命令、安装脚本路径、需求解析逻辑——你都不需要再记**。
