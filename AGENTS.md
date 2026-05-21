# North Star (from installer)

> Source: embedded copy of `DEVELOPMENT_GOALS.md` taken at install time.
> If the source file changes, re-run the installer (or edit this section in sync).

<!-- BEGIN: embedded from DEVELOPMENT_GOALS.md -->
# 开发目标（Development Goals）

> 本文档概括本仓库的**开发目标、边界与成功标准**，供团队对齐、对外介绍与后续演进使用。  
> 方法论细节见 [METHODOLOGY.md](./METHODOLOGY.md)（**§1.3–§1.5**），落地步骤见 [ADOPTION_GUIDE.md](./ADOPTION_GUIDE.md)。

---

## 零、首要前提（不可妥协）

以下三条同等优先，共同约束每一轮检查；落地见 METHODOLOGY §1.3–§1.5。

### 前提一：目标对齐（North Star）

**每一轮检查所提出的修改意见，必须严谨、审慎，且确保推动系统朝本项目的最终目标前进，而不是背离目标。**

| 要求 | 含义 |
|------|------|
| **严谨** | 意见可追溯到可重复证据（探测输出、失败用例、日志、指纹），避免臆测与不可验证的「建议改改」 |
| **审慎** | 默认最小变更；置信不足时不自动落库，而是 `requires_human` 或 `wontfix` |
| **朝向目标** | 意见须能说明如何服务于下文「最终目标」中的至少一项；无法说明则不得进入执行层 |
| **禁止背离** | 不得为「表面变绿」而削弱测试、锁、租约、禁止 auto-fix 列表或人机闸门 |

落地时：**Tester** 产出候选意见 → **Scorer** 逐条打分并判定是否合格 → 仅当轮存在足够 **高分合格意见** 时本轮才算完成，否则与空轮同样加深检查；**Scheduler** 只分派 `value_qualified` 的 Issue；**Executor** 填写 `goal_alignment_note`；**Verifier** 将指标劣化打回 `open`。

**本项目的最终目标（North Star）** — 一切修改意见的判据：

1. **可观测**：缺陷与改进项进入 Issue Store，可被报告与度量（backlog、MTTR、覆盖率）  
2. **可协调**：不破坏 single-writer Scheduler、path lock、executor cap 与 lease  
3. **可验证**：变更后可复跑同一 discovery channel，形成闭环  
4. **有节制**：自动修复仅在策略表与成熟度允许范围内；其余人机协作  
5. **可持续**：长运行进程由 Guardian 保障，而非一次性脚本或「改完即弃」  

若某条意见会损害以上任一项（例如关闭检测以清零 backlog、无验证的大范围重构），**必须拒绝或降级**，即使它能短期减少 Issue 数量。

### 前提二：每轮必有产出（Inspection depth）

**每一轮检查必须提出至少一条修改意见**（发现问题，和/或升级、改进、优化建议）。  
**检查结束后若提不出任何修改意见，则视为本轮检查深度不足，不算完成合格的一轮**——须加深检查（扩展渠道、扩大范围、降阈值、轮换探针），直至产出 **且** 满足前提一。

| 判定 | 含义 |
|------|------|
| **合格一轮** | ≥`min_qualified_per_round` 条 **`value_qualified`** 意见（对齐 + `value_score` 达合格线） |
| **空轮（empty round）** | 零条有效产出 → **检查未完成**，触发深度加深，不得记为「系统健康无需行动」 |
| **深度足够** | 在全部已启用 discovery channels 跑完后，仍能给出可验证的缺陷或对齐 North Star 的改进项 |

**与前提一的关系**：不能为凑数而堆砌无关或背离目标的建议；不能因无缺陷就交白卷。渠道全绿时，Tester **必须**主动产出 `type: improvement`（可观测性、覆盖率、文档漂移、性能基线、自动化自身健康等），并填写 `goal_alignment_note`。

### 前提三：价值评分门槛（Scorer）

**须设专门智能体 Scorer（价值评分者）**，对每一轮提出的每条修改意见，按其对 **最终目标（North Star）的价值/贡献度** 打分并**持久化记录**。

| 要求 | 含义 |
|------|------|
| **逐条打分** | 每条候选意见均有 `value_score`（0–100）与 `value_score_rationale` |
| **合格线** | `value_score >= min_value_score`（配置项，见 `templates/config.example.json`）且通过对齐闸门 → `value_qualified: true` |
| **不合格** | 低于合格线 → **不合格意见**，不计入当轮有效产出；须 **继续检查/加深**，直至提出足够高分值的合格意见 |
| **唯一写分** | 仅 Scorer 可写 `value_score*` 字段；Scheduler 不得分派未合格 Issue（L2+） |

量表见 [templates/scorer_rubric.md](./templates/scorer_rubric.md)。当轮须满足：`合格产出数 >= min_qualified_per_round`（默认 ≥1），且每条合格产出的分值不低于合格线。

**与前提一、二的关系**：有产出但未达标分值 → 视同检查未完成；高分的背离意见仍由对齐闸门否决（可记低分 + `goal_misaligned`）。

---

## 项目命名

| 语言 | 名称 | 说明 |
|------|------|------|
| **英文** | **Qualoop** | *Qual*（质量）+ *loop*（闭环）；读音 /ˈkwɒ luːp/，顺口好记。 |
| **中文** | **质环** | 质量闭环；日常可说「质环检查」。 |

**副标题（中英一致）**：持续自进化的质量闭环方法论  
*A methodology for continuous, bounded self-improvement through quality loops.*

**仓库目录**：建议命名为 `qualoop`（全小写，与 git/submodule 路径一致）。若本地仍为旧目录名，可在文档与远程逐步统一。

---

## 一、项目定位

### 1.1 是什么

从 [LessonVerse](./case-study/LESSONVERSE.md) 自动化实践中抽象出的 **语言无关、可渐进采纳** 的方法论与模板仓库，定义 **五角色**协作模型：

| 角色 | 职责 |
|------|------|
| **Tester** | 持续发现，将多渠道探测结果写入中心化台账 |
| **Scorer** | **价值评分者**：对每条修改意见按 North Star 贡献度打分，判定合格与否 |
| **Scheduler** | 唯一协调者：分派、租约、路径锁与冲突预防（仅分派合格意见） |
| **Executors** | 有界并行执行（fixer / improver / verifier 等可插拔契约） |
| **Guardian** | 监督长运行进程：错峰启动、退避重启、快照报告 |

以 **Issue Store** 为单一事实来源，串联「发现 → **评分** → 分派 → 执行 → 验证 → 监督恢复」全链路。

### 1.2 不是什么

- **不是** 某一应用的业务代码或运行时依赖
- **不是** CI/CD 的替代品（CI 负责合并门禁；本方法论负责长运行发现与本地/预发持续改进）
- **不是** 无约束的「全自动改库」框架（必须有人机协作边界与 auto-fix 策略表）

---

## 二、核心开发目标

### 2.1 方法论产品化（首要）

将零散脚本与一次性探测，提升为可复用、可教学的**通用方法论**：

- 完整描述问题陈述、五角色（含 Scorer）、Issue 生命周期、冲突预防与成熟度模型（L0–L4）
- 提供可复制的配置模板、Issue JSON Schema、Guardian 伪代码与术语表
- 通过案例研究（LessonVerse）诚实呈现「检测到」与「实际修复」的差异，避免过度承诺

### 2.2 可移植与可渐进采纳

使任意中大型软件仓库能在**不绑定语言与框架**的前提下落地：

- 支持 JSON / SQLite / PostgreSQL 等 Store 实现，文件锁 / Redis / etcd 等锁实现
- 采纳路径明确：从 **L1（仅观察 + 人工修复）** 稳定到 **L2（协调层）**，再审慎开启 **L3（有界自动执行）**
- [ADOPTION_GUIDE.md](./ADOPTION_GUIDE.md) 提供分阶段检查清单，允许停在 L1/L2

### 2.3 规模化协作下的质量可观测性

解决「纯人工发现问题 → 人工修复」在中大型项目中的结构性失效：

| 目标 | 对应机制 |
|------|----------|
| 统一缺陷台账 | Issue Store + fingerprint 去重 |
| 避免多人/多 Agent 改同一文件 | Single-writer Scheduler + path lock |
| 探测结论一致进入同一生命周期 | 产品化 discovery channels（health / test / static / E2E） |
| 长运行自动化可靠存活 | Guardian 监督与指数退避 |
| 修了又坏可追溯 | verification 子任务与终态语义 |

### 2.4 与 CI/CD、AI 辅助开发共存

在「人工开发 + CI + AI Agent」并存时代，明确分工：

- **CI**：merge blocking、PR 门禁、一次性 `tester --once` 可接入
- **本方法论**：本地/预发环境长运行循环、积压治理、有界 auto-fix 与报告快照
- 二者通过**同一测试命令与健康检查 URL** 对齐，减少结论分裂

### 2.5 三前提的审查文化（贯穿每轮）

将 **§零** 三条前提落实为可执行纪律，而非口号：

- 每轮意见须 **有产出**（前提二）、**对齐目标**（前提一）、**分值达标**（前提三，Scorer 判定）  
- 空轮或 **低分轮**（无足够 `value_qualified`）→ 加深 discovery，而非宣布「无问题」  
- `improvement` 实行最严对齐审查；无 `goal_alignment_note` 不得进入高分区间  
- 季度评审跟踪 **空轮率**、**低分轮率**、**误导向变更率**、**当轮平均分**（见 METHODOLOGY §9）  

### 2.6 安全与节制的自动修复文化

将「何时不自动修复」写进目标，而非事后补丁：

- 大规模腐化、认证/密钥、架构级变更、低置信度 static 命中等场景必须 **human-in-the-loop**
- Executor 行为受策略表、并发上限（caps）、任务租约（lease）约束
- 原则：**宁可跳过一轮调度，也不允许两个执行者同时写同一文件**

---

## 三、次要开发目标（演进方向）

本仓库当前以**文档与模板**为主；下列能力作为方法论延伸目标，可在参考实现或生态中逐步补齐：

1. **与 CI/CD 双向同步**：GitHub Issues / GitLab 等缺陷平台与 Issue Store 互通  
2. **可插拔 Executor 契约**：fixer / improver / verifier / custom，及外部 Agent API 桥接  
3. **多项目 Guardian 联邦与指标大盘**：MTTR、backlog、误报率、lease 过期率等（见 METHODOLOGY §9）  
4. **人机协作 SLA**：自动修复置信度阈值、审批闸门与 `requires_human` 路由  
5. **成熟度 L4**：持续自主改进（improver + LLM 桥接 + 指标驱动调参），在 L1–L2 稳定后再推进  

---

## 四、成功标准

| 维度 | 可衡量的「完成」信号 |
|------|----------------------|
| **可理解** | 新成员仅读 METHODOLOGY + ARCHITECTURE 即可画出四角色与数据流 |
| **可落地** | 按 ADOPTION_GUIDE 在空白仓库 1–2 天内达到 L1，一周内达到 L2 |
| **可验证** | 案例研究能复现：Tester 产出 Issue、Scheduler dry-run 分配合理、Guardian 崩溃后可恢复 |
| **可信任** | 禁止无界 auto-fix；无背离 North Star；无长期空轮/低分轮却宣称合格；分值可追溯（`value_scores.jsonl`） |
| **可扩展** | 新增 discovery channel 或 Executor 类型不需推翻 Store / Scheduler 契约 |

---

## 五、受众与使用场景

- **平台/效能团队**：在组织内推广统一的质量改进编排模型  
- **业务研发团队**：在自有仓库 `automation/` 中实现参考架构，与现有 CI 互补  
- **AI 辅助开发实践者**：为多个 Coding Agent 提供冲突预防与 Issue 台账，避免并行改库混乱  

---

## 六、文档与仓库结构目标

保持本仓库**独立、零业务耦合**：

- 核心叙述：`METHODOLOGY.md`、`ARCHITECTURE.md`、`ADOPTION_GUIDE.md`  
- 实证与诚实边界：`case-study/LESSONVERSE.md`  
- 机器可读契约：`templates/issue_schema.json`、`templates/config.example.json`  
- 人类可读辅助：`references/glossary.md`  

LessonVerse 等具体实现仅作案例引用路径，**不**作为本仓库依赖。

---

## 七、一句话总结

**Qualoop（质环）** 旨在提供可渐进采纳的**持续自进化质量闭环方法论**，通过 Tester、**Scorer**、Scheduler、Executors、Guardian 五角色与 Issue Store，在规模化协作下保证意见 **对齐目标、必有产出、分值达标**。

---

*文档版本：与仓库方法论同步维护。命名与目标变更时请同步更新 [README.md](./README.md) 首段说明。*
<!-- END: embedded from DEVELOPMENT_GOALS.md -->

---

# AGENTS.md — Qualoop（质环）契约

> 这是本业务项目对所有 AI 编码代理（Codex CLI、Cursor、Claude Code、Gemini CLI、Aider、Amp 等）的**唯一权威契约**。
> 其它专属文件（`CLAUDE.md`、`GEMINI.md`、`.cursor/rules/qualoop.mdc`）都应只作为一行 include 指向本文件。
>
> 方法论源仓库：<https://github.com/sinogenomics/qualoop>（已作为只读 submodule 挂在 `tools/qualoop/`，禁止修改其中文件）
>
> **First-time AI agents on this machine**: read [`tools/qualoop/AI-START-HERE.md`](./tools/qualoop/AI-START-HERE.md) STEP 1 once to ensure the user's personal Qualoop rule is installed. It is idempotent.

---

## 0. North Star（项目最终目标）

<!-- NORTH_STAR_BEGIN -->
**本项目的 North Star（请用 1–3 句填写，所有修改意见以此为判据）：**

- _（示例）让 X 在 Y 场景下达到 Z 体验/性能/可靠性基线。_
- _（请替换为本项目实际目标；未填写时拒绝执行任何 L2+ 操作）_

<!-- NORTH_STAR_END -->

补充判据参见 `tools/qualoop/DEVELOPMENT_GOALS.md` §零。

---

## 1. 触发词 → 动作（用户日常只说这些）

| 用户说 | 你必须做 |
|--------|----------|
| **Qualoop 规划** / **质环规划** | 分析全局目标及 `GOALS.md` / `DEVELOPMENT_GOALS.md`，执行 **Architect / Planner** 规划；输出架构/设计蓝图（如 `docs/ARCHITECTURE_SCHEME.md`）并生成里程碑式的候选 Issue（`type: architecture`）写入台账。 |
| **Qualoop 初始化** / **质环 初始化** | 读 `tools/qualoop/ADOPTION_GUIDE.md` Phase 0–1；仅在**当前业务项目**根下创建 `automation/`、`automation/config.json`（参照 `tools/qualoop/templates/config.example.json`）、最小 L1（IssueStore + Tester + Scorer + `reports/latest_issues.md`）。不动业务源码。 |
| **Qualoop 检查** / **质环检查** | 跑一轮：发现 → Scorer 打分 → 必须产出 ≥ `minQualifiedPerRound` 条 `value_qualified` 意见；更新 `automation/issues.json` 与 `automation/reports/latest_issues.md`；输出当轮合格数、最高分、未合格原因。 |
| **Qualoop 加深检查** / **质环加深** | 上轮空轮或低分：扩展 discovery 渠道（lint、单测、覆盖、E2E、文档漂移、性能基线、自动化自身健康），直至出现高分合格意见；不得交白卷。 |
| **Qualoop 升级到 L2 / L3** | 修改 `qualoop.json` 的 `maturity`，并按 `tools/qualoop/ADOPTION_GUIDE.md` Phase 2/3 启用 Scheduler / Executor 链路；继续受三前提约束。 |
| **Qualoop 执行** | 仅 L3 启用；仅处理 `value_qualified` 且已分配的 Issue；遵守 Executor 策略表；变更后 Verifier 复验。 |

未识别触发词时，按用户自然语言执行，但**仍受第 2 节三前提约束**。

### 1.1 仍未交付过 Qualoop 简报？现在交付

如果本会话尚未向用户输出过 Qualoop 简报（用户首次在本机/本项目接触 Qualoop），**立即输出一次**：

> ✅ 本项目已采用 Qualoop（质环）方法论，成熟度 `<qualoop.json 中的 maturity>`。
>
> 北极星：见本文件 §0 / `NORTH_STAR.md`（如存在）。
>
> 触发词：`Qualoop 检查` / `Qualoop 加深检查` / `Qualoop 升级到 L2/L3`。任何自然语言开发请求都在三前提（目标对齐 / 每轮必有产出 / Scorer ≥ 60）下执行。

之后再处理用户的具体请求。

---

## 2. 三前提（不可妥协，每轮必须满足）

引用 `tools/qualoop/METHODOLOGY.md` §1.3–§1.5：

1. **目标对齐**：每条意见服务上文 North Star，必填 `metadata.goal_alignment_note`；不得为「表面变绿」而削弱测试/检测/lock/lease 或破坏 human-in-the-loop。
2. **每轮必有产出**：每轮至少 1 条合格意见；**禁止只回复「没问题」或「一切正常」**；空轮 = 检查深度不足，必须加深，不得视为完成。
3. **价值评分门槛（Scorer）**：每条意见有 `value_score`（0–100）与 `value_score_rationale`；`value_score >= minValueScore` 且通过对齐闸门 → `value_qualified: true` 才算合格；不合格继续检查。

---

## 3. 五角色边界

引用 `tools/qualoop/METHODOLOGY.md` §2 与 `ARCHITECTURE.md`：

- **Tester** 只发现、不修改业务源码
- **Scorer** 是唯一允许写 `value_score*` 的角色
- **Scheduler** 是唯一分配写入者；L2+ 只分派 `value_qualified` 的 Issue
- **Executor** 在 path lock + lease 内变更；填 `goal_alignment_note`
- **Guardian** 保活长循环，按 backoff 与 stagger 重启
- 同一角色不要在一次交互里同时扮演多个写入者；尤其严禁 Tester 直接改业务源码

---

## 4. 工作区与文件边界（防 AI 改错仓库）

- **写入**：仅当前业务项目根目录及其子目录
- **只读**：`tools/qualoop/`（方法论仓库 submodule），禁止任何修改、移动、删除
- 不在业务项目里复制方法论文档全文；需要引用时使用相对路径 `tools/qualoop/METHODOLOGY.md` 等
- 不在 commit 信息或日志里粘贴方法论全文；引用章节号即可（如 "per METHODOLOGY §1.4"）

---

## 5. 配置

读取**项目根** `qualoop.json`（若不存在请提示用户运行 `tools/qualoop/scripts/install-agents.ps1` 或 `.sh`）：

```json
{
  "methodologyRoot": "tools/qualoop",
  "minValueScore": 60,
  "minQualifiedPerRound": 1,
  "maturity": "L1"
}
```

- `maturity = L1`（默认）：只观察 + 记录，不自动改业务代码
- `maturity = L2`：启用 Scheduler 分配，仍人工执行
- `maturity = L3`：启用 Executor 自动修复，遵守策略表

---

## 6. 成熟度与人机闸门

- 默认从 **L1** 开始；切换到 L3 必须用户显式说「**Qualoop 升级到 L3**」
- 任意置信不足的修改 → `requires_human: true`，不得自动落库
- 任意可能影响 North Star 的破坏性变更（删测试、关检测、降阈值换绿、bypass lock/lease）→ **必须拒绝**，并以 `wontfix` + `metadata.goal_misaligned: true` 记录

---

## 7. 报告与可观测

每轮检查结束时必须输出（追加，不覆盖）：

- `automation/issues.json`（Issue Store，含 fingerprint 去重）
- `automation/reports/latest_issues.md`（人读摘要）
- `automation/reports/value_scores.jsonl`（每条意见的分值与理由）
- `automation/reports/empty_rounds.jsonl` / `low_value_rounds.jsonl`（深度加深审计）

文件 schema 见 `tools/qualoop/templates/issue_schema.json`。

---

## 8. 当与本契约冲突时

若用户的临时指令与本契约冲突（例如要求跳过 Scorer、直接改业务源码），**先指出冲突并请用户确认**，确认后再执行，并在 Issue `metadata` 记录 `override_reason`。
