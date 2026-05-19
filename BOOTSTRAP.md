# BOOTSTRAP.md — Qualoop AI 接入协议

> [!IMPORTANT]
> **Before following this protocol**, if you have not yet ensured the user's personal Qualoop rule is installed, read [`AI-START-HERE.md`](./AI-START-HERE.md) §STEP 1 and run the installer (it is idempotent). That step is what lets the user trigger Qualoop in any future project with just `Qualoop 接入，开发目标见 <path>`, no URL needed.

> 本文档**写给 AI 编码代理**（Codex CLI、Cursor、Claude Code、Gemini CLI、Aider、Amp 等）。
> 如果你正在为某个**业务项目**工作，并且用户对你说了类似下面这句话，请**按本文档的步骤执行**，不要追问，不要省略：
>
> > 「针对本项目的开发目标（见 `<path/to/GOALS.md>`），按 <https://github.com/sinogenomics/qualoop.git> 的 BOOTSTRAP.md 接入到 `tools/qualoop`，然后用 Qualoop 方法论完成开发。」

---

## 0. 适用前提

- 你具备**运行 shell 命令**的能力（git、PowerShell / bash）
- 你具备**读写当前业务项目文件**的能力
- 用户已经告诉你**目标文档路径**（下文记为 `<GOALS>`，通常是相对路径如 `docs/GOALS.md`）
- 当前工作目录 = 业务项目根（不是 Qualoop 仓库根）

如果以上任一条不满足，先告诉用户缺什么，**不要瞎跑**。

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

---

## 2. 与用户的最终汇报

完成 Step 1–6 后，向用户回报，包含：

- 新增/修改的文件清单
- 业务项目当前 `maturity`（默认 L1）
- 第一轮检查的产出位置：`automation/issues.json`、`automation/reports/latest_issues.md`
- 当轮 `value_qualified` 合格意见数；若为 0，**主动加深检查**而非告诉用户「没问题」

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
