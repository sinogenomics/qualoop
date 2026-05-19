# 采纳指南（Adoption Guide）

将 Qualoop 方法论落地到 **任意仓库** 的检查清单。按顺序完成；可停在 L1/L2 而不启用自动修复。

---

## Phase 0：前置条件

- [ ] 项目有明确的 **项目根** 与本地/预发 **运行方式**（如何启前后端）
- [ ] 至少一种 **可重复验证** 手段（测试命令或 health URL）
- [ ] 团队同意：**Scheduler 为唯一分配写入者**
- [ ] 书面化本项目的 **North Star**（可引用或摘录 `DEVELOPMENT_GOALS.md` §零）
- [ ] 团队同意：**每轮检查的修改意见** 须通过目标对齐闸门（METHODOLOGY §1.3），不得为降 Issue 数而背离目标
- [ ] 团队同意：**每轮检查必有产出**（METHODOLOGY §1.4）；空轮视为深度不足，须加深而非「一切正常」
- [ ] 团队同意：设 **Scorer** 对每条意见打分（§1.5）；低于 `min_value_score` 为不合格，须加深直至有足够高分合格意见

---

## Phase 1：目录与配置（L1 Observe）

- [ ] 创建 `automation/`（或 `ops/qualoop/`）
- [ ] 复制并编辑 `templates/config.example.json` → `automation/config.json`
  - [ ] 设置 `backend_url` / `frontend_url`（如适用）
  - [ ] 设置 `intervals_seconds.tester`（建议 ≥120s 起步）
- [ ] 实现或移植 **IssueStore**（见 `templates/issue_schema.json`）
- [ ] 实现 **Tester** 最小集：
  - [ ] 1 个 health URL
  - [ ] 可选：1 个静态检查或 lint 命令
- [ ] 验证：`tester --once` 生成 `issues.json` 且无重复刷屏（fingerprint）
- [ ] 人类报告 `reports/latest_issues.md` **分栏**（见 [templates/reports/latest_issues.template.md](./templates/reports/latest_issues.template.md)）：
  - [ ] **Needs human** — `open` 且 `requires_human`，或 `wontfix` + `terminal_reason: human_required`
  - [ ] **Open / assigned** — 其余非终态
  - [ ] **Resolved**
  - [ ] **Closed / abandoned** — `wontfix` / `duplicate` 且非 `human_required`
- [ ] 反模式：勿将全部 `wontfix` 标为「需人工」
- [ ] 实现 **Scorer**（见 `templates/scorer_loop.pseudo.md`、`scorer_rubric.md`）
- [ ] 配置 `scorer.min_value_score`、`scorer.min_qualified_per_round`
- [ ] 验证：**当轮合格产出**（`value_qualified`）≥ `min_qualified_per_round`；全绿时仍有高分 `improvement`
- [ ] 实现 `reports/value_scores.jsonl`、`empty_rounds.jsonl`、`low_value_rounds.jsonl` + 加深策略
- [ ] 添加人类报告：`reports/latest_issues.md` 生成脚本（含当轮有效产出数）

---

## Phase 2：协调层（L2 Coordinate）

- [ ] 实现 **store_lock** + **path_lock**（文件锁或 Redis）
- [ ] 实现 **Scheduler**（仅分配 `value_qualified == true` 的 Issue）：
  - [ ] `type` → executor 路由表
  - [ ] `max_concurrent` per executor
  - [ ] path conflict 跳过逻辑
  - [ ] `default_lease_minutes`
- [ ] 先用 `scheduler.dry_run: true` 观察分配日志
- [ ] 关闭 dry_run，确认 Issue 变为 `assigned`

---

## Phase 3：执行层（L3 Bounded Execute）

- [ ] 实现 **fixer** 策略表（写明每种 `type` 允许的动作）
- [ ] 实现 **verifier**（复跑失败测试或 health；失败或指标劣化时打回，视为目标背离）
- [ ] 可选：**improver**（仅低风险变更；每条须 `metadata.goal_alignment_note`）
- [ ] Executor `complete_issue` 拒绝无对齐说明的「已解决」
- [ ] 文档化 **禁止自动修复** 列表（认证、大规模腐化、生产）
- [ ] 为 `static`/`health` 配置「仅记录」路径

---

## Phase 4：可靠性（Guardian）

- [ ] 实现 **Guardian** 监督循环（含 **scorer** 子进程；见 `templates/guardian_loop.pseudo.md`）
- [ ] 配置 `initial_backoff_seconds` / `max_backoff_seconds`
- [ ] 配置 `health_stagger_seconds` 启动错峰
- [ ] 提供一键启动：`start.sh` / `start.bat`
- [ ] 日志目录 `automation/logs/` 纳入 `.gitignore`（issues 是否入库由团队决定）

---

## Phase 5：发现渠道扩展

- [ ] 接入单元测试 / `npm test` / `pytest`
- [ ] 接入 linter（ESLint、Ruff、mypy）
- [ ] 可选：Playwright / Cypress **browser_e2e**（`touch_class: external`，须配置 `external_touch_guard`）
  - [ ] **业务终态断言**（成功步骤 / 无错误文案 / 无 error 状态类），禁止「弹窗出现即 pass」
  - [ ] 失败时 `metadata.e2e_outcome`: `pipeline_fail` | `infra_fail`；`pipeline_fail` 附 `metadata.screenshot`
  - [ ] 选择器避免重复 `#id`（LessonVerse 教训）
  - [ ] L3：Verifier 能复跑 E2E **或** 策略表禁止 auto-resolve `browser_e2e`（见 ARCHITECTURE §5.1）
- [ ] 阅读案例模式：[references/EXTERNAL_API_AND_E2E.md](./references/EXTERNAL_API_AND_E2E.md)
- [ ] 遗留脚本纳入 `test_failure` 而非静默失败

---

## Phase 6：CI/CD 集成（可选）

- [ ] CI job：`tester --once` 失败时非零退出或上传 `issues.json` artifact
- [ ] 不在 CI 中运行 Guardian 无限循环
- [ ] PR 模板：链接 `latest_issues.md` 或 backlog 指标
- [ ] 可选：bi-directional sync 到 GitHub Issues

---

## Phase 7：治理与指标

- [ ] 定义 **MTTR**、**backlog**、**false positive**、**empty round rate**、**low-value round rate**、**round mean value score**、**goal-misaligned change rate**（周报）
- [ ] 指定 **human-in-the-loop** 负责人（腐化还原、密钥）
- [ ] 季度评审：成熟度是否可从 L2 升到 L3；并抽查当轮修改意见是否背离 North Star

---

## 反模式（避免）

| 反模式 | 后果 |
|--------|------|
| 多个 Scheduler 或无锁写 Store | 重复分配、JSON 损坏 |
| Executor 自行改 `assigned_executor` | 抢单与覆盖 |
| Tester 直接改代码且无 verifier | 不可追溯、误修 |
| 无 lease 的长任务 | 永久 assigned 堵塞队列 |
| E2E 使用全局 `#id` 且 DOM 重复 | strict mode 误报（见 LessonVerse） |
| 每轮 `/health` 打 external live API（OAuth `--test` 等） | 第三方限流/封号；性能误报 |
| 无 liveness/readiness 分层 | 自动化与人工共用昂贵 health |
| E2E「技术步骤完成」当 pass，忽略业务错误 UI | 假绿；用户故障不进 Issue Store |
| 报告把所有 `wontfix` 标为「需人工」 | 维护者过载；真正阻塞项被淹没 |
| 空轮加深时优先开全量 E2E 而非 lint/static | 加剧 external 触达与成本 |

---

## 最小文件清单（参考 LessonVerse）

```
automation/
  __init__.py          # 或 package 等价物
  config.json
  paths.py             # 布局与配置加载
  issue_store.py
  locks.py
  logging_util.py
  tester.py
  scheduler.py
  guardian.py
  browser_e2e.py       # 可选
  executors/
    base.py
    fixer.py
    improver.py
    verifier.py
  reports.py
```

---

## 验收标准

| 级别 | 验收 |
|------|------|
| L1 | Tester 运行 24h，Issue 有去重，报告可读 |
| L2 | 两条冲突 path 的 Issue 不会同时 assigned |
| L3 | fixer 处理 health 不修改代码；verifier 能关闭子任务 |
| L4 | improver/LLM 有审批闸门；指标周报稳定 |

完成采纳后，可将本项目 `case-study/LESSONVERSE.md` 与自家案例并列，形成组织内知识库。
