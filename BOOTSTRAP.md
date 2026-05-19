# BOOTSTRAP.md — Qualoop AI 接入协议

> [!IMPORTANT]
> ## 致 AI：你来到这里 = 用户用 URL 引你来的；目标应当也已经给你了
>
> 在跑本协议之前，请确认两件事：
>
> 1. **你已经看过用户原消息了**，并且按 [`AI-START-HERE.md`](./AI-START-HERE.md) §STEP 0 解析出 **North Star**（一份文档路径或一句话）。**没解析出就别跑下面的步骤**——先回头看用户那条消息，找到目标；找不到就向用户问一次。
> 2. 用户的**个人规则**已经装过（`AI-START-HERE.md` §STEP 1 是幂等的，直接跑一遍即可）。
>
> 这两件确认完毕，再继续 §0.5 → §1。

> 本文档**写给 AI 编码代理**（Codex CLI、Cursor、Claude Code、Gemini CLI、Aider、Amp 等）。
> 如果你正在为某个**业务项目**工作，并且用户对你说了类似下面这句话，请**按本文档的步骤执行**，不要追问，不要省略：
>
> > 「针对本项目的开发目标（见 `<path/to/GOALS.md>`），按 <https://github.com/sinogenomics/qualoop.git> 的 BOOTSTRAP.md 接入到 `tools/qualoop`，然后用 Qualoop 方法论完成开发。」

---

## 0. 适用前提

- 你具备**运行 shell 命令**的能力（git、PowerShell / bash）
- 你具备**读写当前业务项目文件**的能力
- 当前工作目录 = 业务项目根（不是 Qualoop 仓库根）

如果以上任一条不满足，先告诉用户缺什么，**不要瞎跑**。

---

## 0.5 解析用户输入（识别北极星来源）

用户首条消息通常**只给两件事**：Qualoop 仓库链接 + 项目需求。需求有两种形态：

- **(A) 文件路径**：`docs/GOALS.md`、`需求.md`、`requirements.txt` 等
- **(B) 一句话目标**：「让 X 在 Y 场景下可靠运行」

按以下顺序识别：

1. 把 Qualoop URL 从消息里挑出去
2. 剩余文本里找候选路径：含 `/` 或 `\` 的 token，或 `.md`/`.txt`/`.rst`/`.pdf`/`.docx`/`.json` 结尾，或「见 X」/「需求文档 X」/「目标见 X」/「per X」之后的字符串
3. 候选路径用 `test -f` / `Test-Path` 验证存在 → 走模式 **(A)**，Step 3 用 `--north-star-file <path>` / `-NorthStarFile <path>`
4. 候选路径不存在 → 一次性问用户，列出最相似的 `*GOAL*` / `*目标*` / `*需求*` / `*PRD*` / `*REQUIREMENT*` 候选
5. 零候选 → 走模式 **(B)**，整段剩余自然语言作为一句话，Step 3 用 `--north-star "<text>"` / `-NorthStar "<text>"`
6. 多个候选 → 文件名匹配 `(?i)GOAL|目标|需求|REQUIREMENT|PRD|SPEC` 优先；仍歧义问一次

不要反复追问；能从消息直接推断的就直接做。下文 `<GOALS>` 指你解析出的路径或一句话。

---

## 1. 执行步骤（按顺序，遇错即停并向用户报告）

### Step 1：确认或初始化 Git 仓库

```bash
# 如果业务项目不是 git 仓库
git init
```

仅在 `.git` 不存在时执行 `git init`。已是仓库则跳过。

### Step 2：添加 Qualoop 子模块

```bash
git submodule add https://github.com/sinogenomics/qualoop.git tools/qualoop
git submodule update --init --recursive
```

如果 `tools/qualoop/` 已存在且包含 `METHODOLOGY.md`，**跳过此步**并继续。

### Step 3：运行安装脚本（按平台选其一）

**Windows / PowerShell**：

```powershell
.\tools\qualoop\scripts\install-agents.ps1 -TargetProject . -NorthStarFile "<GOALS>"
```

**macOS / Linux / WSL**：

```bash
./tools/qualoop/scripts/install-agents.sh --target . --north-star-file "<GOALS>"
```

把上面 `<GOALS>` 替换为用户给你的目标文档路径（用户原话里的路径）。

> 若用户给的是**绝对路径**或位于业务项目之外，安装脚本会自动把它复制为业务项目根的 `NORTH_STAR.md`。无需特殊处理。
>
> 若用户**没有给路径**，且目标只是一句话字符串，改用：
> - PowerShell：`-NorthStar "<那句话>"`
> - bash：`--north-star "<那句话>"`

### Step 4：验证安装

确认业务项目根下生成了以下文件：

- `AGENTS.md`（顶部含 `# North Star (from installer)` 段）
- `CLAUDE.md`、`GEMINI.md`
- `qualoop.json`

如果任一缺失，**停下来报错**，不要进入下一步。

### Step 5：提交安装产物

```bash
git add -A
git commit -m "Add Qualoop AI contract and submodule"
```

如果 git 没有 `user.name` / `user.email`，**先问用户**怎么配置，不要擅自设。

### Step 6：切换到契约模式继续工作

从此刻起：

1. **你的所有后续行为必须遵守业务项目根的 `AGENTS.md`**（含三前提、五角色、触发词、边界）
2. **不要修改 `tools/qualoop/` 里任何文件**（只读 submodule）
3. 默认 `maturity = L1`：只发现、记录、打分；**不要大范围自动改业务代码**
4. 进入第一轮检查：等价于用户说了「**Qualoop 初始化**」，按 `AGENTS.md` 第 1 节触发词表执行

### Step 7：向用户输出 Qualoop 简报（必做）

第一轮检查完成后，**主动**向用户输出以下内容（用用户的语言，下面给的是中文示例）：

```markdown
✅ Qualoop 已接入本项目（成熟度 L1）。

**北极星（North Star）**：<这里写解析到的 North Star（文件路径或一句话）>

**生成的文件**：
- `AGENTS.md` / `CLAUDE.md` / `GEMINI.md` —— AI 契约（任何 AI 工具都自动读）
- `qualoop.json` —— 配置（minValueScore=60, maturity=L1）
- `tools/qualoop/` —— 方法论 submodule（只读）
- `automation/` —— 第一轮检查产物

**第一轮检查结果**：
- 合格意见 N 条（最高分 X，最低分 Y）
- 报告：`automation/reports/latest_issues.md`

**从现在起你只需要说**：

| 你说 | 我做 |
|------|------|
| `Qualoop 检查` | 跑下一轮：发现 → Scorer → 写报告 |
| `Qualoop 加深检查` | 上轮空轮/低分时扩展渠道，直到出现高分合格意见 |
| `Qualoop 升级到 L2` | 启用 Scheduler 分配，仍人工执行 |
| `Qualoop 升级到 L3` | 启用 Executor 自动修复，受策略表与三前提约束 |
| 任何自然语言开发请求 | 我都在 Qualoop 契约下执行 |

**三前提（我永远不会违反）**：目标对齐 / 每轮必有产出 / Scorer 打分 ≥ 60

需要时可读：`tools/qualoop/METHODOLOGY.md`、`tools/qualoop/DEVELOPMENT_GOALS.md`
```

把 `<...>` 占位符全部替换成实际值后输出。这是用户对 Qualoop 仪式感的**唯一一次接触点**——务必完整、不省略。

---

## 2. 与用户的最终汇报

Step 7 即最终汇报。汇报后保持沉默等待用户下一条指令；不要继续自由发挥改代码。

---

## 3. 常见错误的应对

| 现象 | 应对 |
|------|------|
| `git submodule add` 报错说 `tools/qualoop` 已存在 | 检查里面是否已是 Qualoop 内容；是 → 跳过 Step 2；不是 → 报告用户冲突 |
| 找不到 `<GOALS>` 文件 | 告诉用户路径有误，列出业务项目已有的候选目标文档（`*GOAL*.md`、`*OBJECTIVE*.md`、`README.md` 等），让用户确认 |
| PowerShell 执行策略阻止脚本 | 告知用户运行：`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`；不要自动改全局策略 |
| 业务项目非 git 仓库且用户拒绝 `git init` | 用 `git clone` 方式：`git clone --depth=1 https://github.com/sinogenomics/qualoop.git tools/qualoop`；其余步骤照常，最后**仍要提交**（前提是项目至少是 git 仓库；否则告知用户改用 git init） |

---

## 4. 给用户的一句话模板（用户可直接复制）

```
针对本项目的开发目标（见 docs/GOALS.md），按 https://github.com/sinogenomics/qualoop.git
的 BOOTSTRAP.md 接入到 tools/qualoop，然后用 Qualoop 方法论完成开发。
```

把 `docs/GOALS.md` 替换为本项目实际目标文档路径即可。

---

## 5. 关键不变式（无论如何不可违反）

1. **不在 Qualoop 仓库（`tools/qualoop/`）里改任何文件**
2. **不绕过三前提**（目标对齐 / 每轮必有产出 / Scorer 打分）
3. **L1 阶段不大范围改业务源码**；置信不足一律 `requires_human`
4. **每轮检查必须产出至少 1 条 `value_qualified` 意见**；为 0 时加深，不可交白卷
5. **删测试 / 关检测 / 降阈值换绿一律拒绝**，记为 `wontfix` + `metadata.goal_misaligned: true`
