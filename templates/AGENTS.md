# AGENTS.md — Qualoop（质环）契约

> 这是本业务项目对所有 AI 编码代理（Codex CLI、Cursor、Claude Code、Gemini CLI、Aider、Amp 等）的**唯一权威契约**。
> 其它专属文件（`CLAUDE.md`、`GEMINI.md`、`.cursor/rules/qualoop.mdc`）都应只作为一行 include 指向本文件。
>
> 方法论源仓库：<https://github.com/sinogenomics/qualoop>（已作为只读 submodule 挂在 `tools/qualoop/`，禁止修改其中文件）

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
| **Qualoop 初始化** / **质环 初始化** | 读 `tools/qualoop/ADOPTION_GUIDE.md` Phase 0–1；仅在**当前业务项目**根下创建 `automation/`、`automation/config.json`（参照 `tools/qualoop/templates/config.example.json`）、最小 L1（IssueStore + Tester + Scorer + `reports/latest_issues.md`）。不动业务源码。 |
| **Qualoop 检查** / **质环检查** | 跑一轮：发现 → Scorer 打分 → 必须产出 ≥ `minQualifiedPerRound` 条 `value_qualified` 意见；更新 `automation/issues.json` 与 `automation/reports/latest_issues.md`；输出当轮合格数、最高分、未合格原因。 |
| **Qualoop 加深检查** / **质环加深** | 上轮空轮或低分：扩展 discovery 渠道（lint、单测、覆盖、E2E、文档漂移、性能基线、自动化自身健康），直至出现高分合格意见；不得交白卷。 |
| **Qualoop 执行** | 仅 L3 启用；仅处理 `value_qualified` 且已分配的 Issue；遵守 Executor 策略表；变更后 Verifier 复验。 |

未识别触发词时，按用户自然语言执行，但**仍受第 2 节三前提约束**。

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
