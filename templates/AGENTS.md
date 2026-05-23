# North Star (from installer)

> Source: see [`GOALS.md`](./GOALS.md) (single source of truth, not embedded).
> AI agents MUST read that file before producing any opinion this round.

@GOALS.md

---

# AGENTS.md — Qualoop（质环）契约

> 这是本业务项目对所有 AI 编码代理（Codex CLI、Cursor、Claude Code、Gemini CLI、Aider、Amp 等）的**唯一权威契约**。
>
> 方法论源仓库：<https://github.com/sinogenomics/qualoop>（已作为只读 submodule 挂在 `tools/qualoop/`，禁止修改其中文件）

---

## 0. North Star（项目最终目标）

<!-- NORTH_STAR_BEGIN -->
**本项目的 North Star（请用 1–3 句填写，所有修改意见以此为判据）：**

- 面向 K-12 学生、自学者 and 家长辅导场景，允许用户上传课本内容照片后，在本地可靠地一键整理并生成和下载多种高品质学习材料（包括音频讲解、视频讲解、信息图与思维导图、Slides）。
- 通过稳定健全的本地 AI 命令行调度，在任何网络、分辨率、超时或认证异常时提供清晰透明的中文错误引导，确保本地全链路端端运行的极高稳定性。

<!-- NORTH_STAR_END -->

补充判据参见 `tools/qualoop/DEVELOPMENT_GOALS.md` §零。

---

## 1. 触发词 → 动作（用户日常只说这些）

| 用户说 | 你必须做 |
|--------|----------|
| **Qualoop 初始化** / **质环 初始化** | 读 `tools/qualoop/ADOPTION_GUIDE.md`；仅在**当前业务项目**根下创建 `automation/` 与必要工具环境。不动业务源码。 |
| **Qualoop 检查** / **质环检查** | 跑一轮：发现 → Scorer 打分 → 必须产出合格意见并自动分派和执行修复；更新 `automation/issues.json` 与 `automation/reports/latest_issues.md`。 |
| **Qualoop 加深检查** / **质环加深** | 上轮空轮或低分：扩展 discovery 渠道（lint、单测、覆盖、E2E、文档漂移、性能基线、自动化自身健康），直至出现高分合格意见；不得交白卷。 |
| **Qualoop 执行** | 处理合格的且已分配的 Issue；遵守 Executor 策略表；变更后 Verifier 复验。 |

未识别触发词时，按用户自然语言执行，但**仍受第 2 节三前提约束**。

### 1.1 仍未交付过 Qualoop 简报？现在交付

如果本会话尚未向用户输出过 Qualoop 简报（用户首次在本机/本项目接触 Qualoop），**立即输出一次**：

> ✅ 本项目已采用 Qualoop（质环）全自动闭环自愈开发方法论。
>
> 北极星：见本文件 §0 / `NORTH_STAR.md`（如存在）。
>
> 触发词：`Qualoop 检查` / `Qualoop 加深检查`。任何自然语言开发请求都在三前提（目标对齐 / 每轮必有产出 / Scorer ≥ 60）下执行。

之后再处理用户的具体请求。

---

## 2. 三前提（不可妥协，每轮必须满足）

1. **目标对齐**：每条意见服务上文 North Star，必填 `metadata.goal_alignment_note`；不得为「表面变绿」而削弱测试/检测/lock/lease 或破坏 human-in-the-loop。
2. **每轮必有产出**：每轮至少 1 条合格意见；**禁止只回复「没问题」或「一切正常」**；空轮 = 检查深度不足，必须加深，不得视为完成。
3. **价值评分门槛（Scorer）**：每条意见有 `value_score`（0–100）与 `value_score_rationale`；`value_score >= minValueScore` 且通过对齐闸门 → `value_qualified: true` 才算合格；不合格继续检查。

---

## 3. 五角色边界

- **Tester** 只发现、不修改业务源码
- **Scorer** 是唯一允许写 `value_score*` 的角色
- **Scheduler** 是唯一分配写入者，只分派 `value_qualified` 的 Issue
- **Executor** 在 path lock + lease 内变更；填 `goal_alignment_note`
- **Guardian** 在系统后台常驻运行并对整个闭环链路进行保活监管，按 backoff 与 stagger 重启各角色
- 同一角色不要在一次交互里同时扮演多个写入者；尤其严禁 Tester 直接改业务源码

---

## 4. 工作区与文件边界（防 AI 改错仓库）

- **写入**：仅当前业务项目根目录及其子目录
- **只读**：`tools/qualoop/`（方法论仓库 submodule），禁止任何修改、移动、删除
- 不在业务项目里复制方法论文档全文；需要引用时使用相对路径 `tools/qualoop/METHODOLOGY.md` 等
- 不在 commit 信息或日志里粘贴方法论全文；引用章节号即可（如 "per METHODOLOGY §1.4"）

---

## 5. 配置

读取**项目根** `qualoop.json`：

```json
{
  "methodologyRoot": "tools/qualoop",
  "minValueScore": 60,
  "minQualifiedPerRound": 1
}
```

Qualoop 默认启用 Executor 自动修复，遵守 `automation/EXECUTOR_POLICY.md`。

---

## 6. 人机闸门

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
