# Qualoop · 质环

> 建议仓库目录名：`qualoop` · 开发目标见 [DEVELOPMENT_GOALS.md](./DEVELOPMENT_GOALS.md)

**持续自进化的质量闭环方法论** — 从 LessonVerse 自动化实践中抽象，适用于大多数中大型软件项目。

## 愿景

在人工开发、CI 与 AI 辅助并存的时代，单靠「人发现问题 → 人修」无法在规模上保持可观测性与持续改进。本方法论定义 **语言无关、可渐进采纳** 的五角色模型：发现（Tester）、**价值评分（Scorer）**、协调（Scheduler）、执行（Executors）、监督（Guardian），以 **Issue Store** 串联全链路。

**首要前提**（见 [DEVELOPMENT_GOALS.md](./DEVELOPMENT_GOALS.md) §零、[METHODOLOGY.md](./METHODOLOGY.md) §1.3–§1.5）：

1. 意见须严谨、审慎，**朝向** 最终目标、**不背离** 目标  
2. **每轮必须提出修改意见**；提不出 = 检查深度不足，须加深检查  
3. **Scorer 对每条意见按 North Star 贡献度打分**；低于合格线 = 不合格，须继续检查直至有足够高分合格意见

---

## 给用户：对 AI 说**一句话**即可接入（推荐）

把下面这句话发给你的 AI（Codex CLI / Cursor / Claude Code / Gemini CLI / Aider / Amp 等任意一个）：

```
针对本项目的开发目标（见 docs/GOALS.md），按 https://github.com/sinogenomics/qualoop.git
的 BOOTSTRAP.md 接入到 tools/qualoop，然后用 Qualoop 方法论完成开发。
```

把 `docs/GOALS.md` 改成你项目实际的目标文档路径即可。AI 会自动：

1. 抓取本仓库 [`BOOTSTRAP.md`](./BOOTSTRAP.md)
2. 加 submodule `tools/qualoop` → 跑 `install-agents` → 生成业务项目根的 `AGENTS.md` / `CLAUDE.md` / `GEMINI.md` / `qualoop.json`
3. 进入 Qualoop 契约模式，从 L1 开始按方法论开发

之后日常对 AI 只说一句：「**Qualoop 检查**」。

> 没有目标文档？可以把括号里改成一句话：`(目标是：让 X 在 Y 场景下可靠运行)`。详见 [`templates/prompts/oneliner.md`](./templates/prompts/oneliner.md)。

### 话术再短一档：配置一次个人规则

不想每次写 URL？把 [`templates/personal/qualoop.personal-rule.md`](./templates/personal/qualoop.personal-rule.md) 里那段规则**粘到你 AI 工具的用户配置**一次（Cursor User Rules、`~/.claude/CLAUDE.md`、`~/.codex/AGENTS.md`、`~/.gemini/GEMINI.md` 等），之后新项目首句话术就变成：

```
Qualoop 接入，开发目标见 docs/GOALS.md
```

—— 不用再写 URL，不用再写 BOOTSTRAP.md，不用再写 tools/qualoop。AI 看到「Qualoop 接入」触发词会自动按个人规则去拉 BOOTSTRAP.md 完成接入。详见 [`templates/personal/`](./templates/personal/)。

---

## 跨 AI 工具落地（手动版本，供脚本/CI 使用）

如果你想自己跑命令而不是让 AI 跑：

```powershell
# Windows / PowerShell — pick ONE form of North Star
cd path\to\your-app
git submodule add https://github.com/sinogenomics/qualoop.git tools/qualoop

# (a) one-line goal
.\tools\qualoop\scripts\install-agents.ps1 -TargetProject . -NorthStar "<your one-line goal>"
# (b) the goal is already in a document → embed it
.\tools\qualoop\scripts\install-agents.ps1 -TargetProject . -NorthStarFile docs\GOALS.md
# (c) just link to that document, do not embed (single source of truth)
.\tools\qualoop\scripts\install-agents.ps1 -TargetProject . -NorthStarFile docs\GOALS.md -LinkOnly
```

```bash
# macOS / Linux / WSL — pick ONE form of North Star
cd path/to/your-app
git submodule add https://github.com/sinogenomics/qualoop.git tools/qualoop

# (a) one-line goal
./tools/qualoop/scripts/install-agents.sh --target . --north-star "<your one-line goal>"
# (b) the goal is already in a document → embed it
./tools/qualoop/scripts/install-agents.sh --target . --north-star-file docs/GOALS.md
# (c) just link to that document, do not embed
./tools/qualoop/scripts/install-agents.sh --target . --north-star-file docs/GOALS.md --link-only
```

> If the goal file lives outside the business project, the installer will copy it to `NORTH_STAR.md` in the project root automatically.

脚本会在业务项目根生成（每项都有用途，可被 git 追踪）：

| 文件 | 谁会读 |
|------|--------|
| `AGENTS.md` | **唯一权威契约**；Codex CLI、Cursor 1.x、Aider、Amp、Jules 等原生读取 |
| `CLAUDE.md` | Claude Code（一行 include 指向 `AGENTS.md`） |
| `GEMINI.md` | Gemini CLI（一行 include 指向 `AGENTS.md`） |
| `qualoop.json` | 所有工具共用：`maturity`、`minValueScore`、`methodologyRoot` |
| `tools/qualoop/` | 方法论 submodule（只读） |

日常话术只剩两句（见 [`templates/prompts/`](./templates/prompts/)）：

```
Qualoop 初始化
本项目 North Star：<一句话目标>     # 仅首次
```
```
Qualoop 检查                       # 每轮
```

> 没有 `AGENTS.md`？AI 会把任何 Qualoop 触发词当普通指令处理，**三前提将失效**。请先跑安装脚本。

---

未来优化方向（本仓库为方法论与模板，非运行时实现）：

- 与 CI/CD（GitHub Actions、GitLab CI 等）双向同步 issue
- 可插拔 Executor 契约（fixer / improver / verifier / custom）
- 多项目 Guardian 联邦与指标大盘
- 人机协作 SLA：自动修复置信度阈值与审批闸门

## 文档地图

| 文件 | 用途 |
|------|------|
| [DEVELOPMENT_GOALS.md](./DEVELOPMENT_GOALS.md) | **开发目标**、项目命名、边界与成功标准 |
| [METHODOLOGY.md](./METHODOLOGY.md) | **核心方法**（三前提、五角色、生命周期、成熟度等） |
| [templates/scorer_rubric.md](./templates/scorer_rubric.md) | Scorer 价值评分量表 |
| [templates/scorer_loop.pseudo.md](./templates/scorer_loop.pseudo.md) | Scorer 主循环伪代码 |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | 角色职责、数据流、锁与冲突模型 |
| [ADOPTION_GUIDE.md](./ADOPTION_GUIDE.md) | 在任意仓库落地的检查清单 |
| [case-study/LESSONVERSE.md](./case-study/LESSONVERSE.md) | LessonVerse 实证：发现了什么、修了什么 |
| [BOOTSTRAP.md](./BOOTSTRAP.md) | **写给 AI 的接入协议**：用户一句话 → AI 自动完成 submodule + 安装 + 进入契约 |
| [templates/personal/](./templates/personal/) | **个人级 AI 规则**：粘贴一次到你的 AI 工具用户配置，所有新项目自动接入 |
| [templates/AGENTS.md](./templates/AGENTS.md) | **跨 AI 工具权威契约**（推荐）：Codex/Cursor/Aider/Amp 原生读取 |
| [templates/CLAUDE.md](./templates/CLAUDE.md) · [templates/GEMINI.md](./templates/GEMINI.md) | Claude Code / Gemini CLI 入口（一行 include → `AGENTS.md`） |
| [templates/prompts/](./templates/prompts/) | 极短话术备查：`init.md` / `check.md` / `deepen.md` |
| [scripts/install-agents.ps1](./scripts/install-agents.ps1) · [.sh](./scripts/install-agents.sh) | 一键安装到业务项目（跨平台） |
| [templates/qualoop.cursor.rule.mdc](./templates/qualoop.cursor.rule.mdc) | Cursor 旧版规则（兼容；新项目用 `AGENTS.md` 即可） |
| [templates/qualoop.cursor.json.example](./templates/qualoop.cursor.json.example) | Cursor 旧版配置示例（兼容） |
| [templates/](./templates/) | 配置、Issue JSON Schema、Guardian 伪代码 |
| [references/glossary.md](./references/glossary.md) | 术语表 |
| [reports/development-report.html](./reports/development-report.html) | **开发过程报告**（网页，含 Cursor 话术） |
| [references/PROFESSIONAL_SETUP.md](./references/PROFESSIONAL_SETUP.md) | **专业用法**：一次配置，日常一句 |
| [references/CURSOR_USAGE.md](./references/CURSOR_USAGE.md) | Cursor 长话术备查 |

## 与具体项目的关系

本目录 **独立** 于任何应用仓库。LessonVerse 实现位于 `lessonverse/automation/`；仅作为 [案例研究](./case-study/LESSONVERSE.md)，**无代码耦合**。

## 快速开始（概念）

1. 阅读 `METHODOLOGY.md` 理解五角色与成熟度模型；或打开 [开发过程报告](./reports/development-report.html) 总览。
2. 按 `ADOPTION_GUIDE.md` 在目标项目中创建 `automation/`（或等价目录）。
3. 复制 `templates/config.example.json` 与 `templates/issue_schema.json` 并按项目调整。
4. 从 **L1**（仅 Tester + 人工）起步，再启用 Scheduler 与 Executors。

## 许可与贡献

方法论文档可自由在组织内复用与改编；引用 LessonVerse 案例时请注明来源路径，勿将本仓库与 LessonVerse 运行时混为一谈。
