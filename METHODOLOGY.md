# Qualoop 通用方法论

> **Qualoop Universal Methodology**  
> 中文为主叙述，关键概念保留英文术语以便与代码、配置和业界文献对齐。

---

## 1. 问题陈述（Problem Statement）

### 1.1 为什么「纯人工开发」在中大型项目中会失效

| 现象 | 根因 |
|------|------|
| 回归在用户侧才发现 | 发现渠道分散，无统一 Issue 台账 |
| 多人/多 Agent 同时改同一文件 | 缺少 **single-writer Scheduler** 与 **path lock** |
| 环境、健康检查、E2E 与单元测试结论不一致 | 探测未产品化，未进入同一 **lifecycle** |
| 自动化脚本本身腐化或与主应用脱节 | 无 **Guardian** 监督循环进程与退避重启 |
| 「修了又坏」无法追溯 | Issue 无 **fingerprint** 去重与 **verification** 闭环 |

**结论**：需要一套与语言、框架解耦的 **持续发现 → 协调分派 → 有界执行 → 监督恢复** 机制，而不是零散脚本或一次性 CI。

### 1.2 本方法论解决什么

- 将各类 **Discovery channels** 的输出统一为 **Issue**
- 用 **Scheduler** 保证同一时刻同一资源只有一个执行者
- 用 **Executor caps** 与 **task lease** 限制并行与僵尸任务
- 用 **Guardian** 保证长运行进程在崩溃后仍存活
- 明确 **何时不自动修复**（human-in-the-loop）
- 保证每轮意见 **目标对齐**（§1.3）、**必有产出**（§1.4）、**分值达标**（§1.5，Scorer）

---

## 1.3 目标对齐前提（Prerequisite: Goal Alignment）

> **前提一（不可妥协）**：每轮检查提出的修改意见，必须严谨、审慎，确保让系统朝着最终目标走，而不是背离最终目标。

### 1.3.1 范围与判据

| 概念 | 范围 |
|------|------|
| **每轮检查** | Tester 一轮 discovery；Scheduler 一轮分配；Executor 一次处理；Verifier 一次复验；报告/人工评审 |
| **修改意见** | 新建/更新的 Issue、执行 note、diff、`improvement` 建议、报告行动项 |

**North Star** 以 [DEVELOPMENT_GOALS.md](./DEVELOPMENT_GOALS.md) 前提一为准。背离示例：为降 Issue 关渠道、跳过测试、破坏 lock/lease、L1 阶段做 L3 级 auto-fix、无法复验的「已解决」。

### 1.3.2 执行要求

| 原则 | 要求 |
|------|------|
| **严谨** | 绑定可复现证据（命令、日志、截图、`paths`） |
| **审慎** | 不确定则 `requires_human`；不强行落库改代码 |
| **朝向目标** | `metadata.goal_alignment_note` 说明服务 North Star 哪一项、如何验证 |
| **可否决** | 无法对齐 → `wontfix` + `metadata.goal_misaligned: true` |

### 1.3.3 五角色闸门

- **Tester**：事实型 Issue 为主；`improvement` 须有可验证收益假设  
- **Scorer**：逐条打分；低于合格线标 `value_insufficient`，不计入合格产出  
- **Scheduler**：拒绝无关 `improvement`；L2+ 仅分派 `value_qualified`；L3 前 improver 无 `goal_alignment_note` 不分配  
- **Executor**：`complete_issue` 的 note 须含对齐理由，否则 `resolved=false`  
- **Verifier**：指标劣化或范围漂移 → 打回 `open`  

人工与 LLM 建议适用同一闸门；**均须经 Scorer 评分**后方可计入合格轮次。

---

## 1.4 每轮必有产出前提（Prerequisite: Mandatory Round Output）

> **前提二（不可妥协）**：每一轮检查必须提出修改意见。提不出修改意见 = 检查深度不够；深度足够则一定能发现问题，或提出升级/改进/优化意见。

### 1.4.1 合格一轮的定义

一轮 Tester discovery → Scorer 评分结束后，须满足：

```
合格产出数（value_qualified == true）≥ min_qualified_per_round  （默认 ≥ 1）
```

**有效产出** = 下列至少一类，且同时通过 §1.3 目标对齐闸门与 §1.5 价值评分门槛（`value_qualified: true`）：

| 类别 | Issue `type` 或形式 | 示例 |
|------|---------------------|------|
| **发现问题** | `health`, `test_failure`, `static`, `browser_e2e`, `verification` | 探针失败、回归、lint 命中 |
| **改进/优化** | `improvement`（`metadata.output_kind`: `improvement` \| `optimization`） | 覆盖率盲区、文档漂移、间隔调优、可观测性补强 |

**不算有效产出**：仅重复已有 fingerprint 的刷屏；已被 `goal_misaligned` 否决的建议；`value_score < min_value_score` 的低分意见；空报告或「一切正常」且无行动项。

### 1.4.2 空轮（Empty round）与深度加深

若一轮结束 **有效产出数 = 0**：

1. **不得**将本轮记为成功或「无需行动」  
2. **必须**记录 `reports/empty_rounds.jsonl`（或等价）含：时间戳、已跑 channels、加深动作  
3. **必须**触发至少一项 **深度加深**（下轮执行）：

| 加深动作 | 说明 |
|----------|------|
| 扩展 channels | 启用尚未跑的 test / static / E2E |
| 扩大范围 | 增加扫描路径、依赖、配置目录 |
| 降阈值 | 将 warning 级 lint、性能回退、陈旧依赖纳入 `improvement` |
| 轮换探针 | 按配置轮换 health 深度检查、冒烟子集 |
| 元检查 | 对 automation 脚本自身跑 static / 单测 |

**原则**：检查深度足够 → 必能产出；产不出 → 继续加深，而非停止检查。

### 1.4.3 全绿场景下的改进义务

当所有强制 channels 当轮均无 `defect` 时，Tester **仍须**创建 ≥1 条 `type: improvement`，例如：

- 测试或 E2E 覆盖缺口（附 `paths` 与复现建议）  
- backlog 陈旧 Issue 清理、租约过期治理  
- 报告可读性、指标导出、channel 轮换配置  
- 依赖/工具链小版本、文档与实现不一致  

每条须 `goal_alignment_note`，说明如何巩固 North Star（通常「可观测」或「可验证」）。

### 1.4.4 与前提一、前提三的合取

| 场景 | 处理 |
|------|------|
| 有产出、对齐且高分合格 | **合格一轮** |
| 有产出但对齐失败 | 否决；无其他合格产出 → **空轮/低分轮**，加深检查 |
| 有产出但分值不足 | **低分轮**；Scorer 记 `value_insufficient`；加深检查直至 ≥`min_qualified_per_round` 条合格 |
| 无产出 | **空轮**，加深检查 |
| 仅重复 duplicate | 当轮无新合格 fingerprint → 按 **空轮** 处理 |
| 渠道因触达预算被跳过 | 记 `reports/throttled_channels.jsonl`；**不算空轮**（见 §1.6） |

Guardian 快照报告应列出当轮 **合格产出数**、**最高分**、**平均分**；连续空轮或低分轮应告警。

---

## 1.5 价值评分前提（Prerequisite: Value Scoring / Scorer）

> **前提三（不可妥协）**：设专门智能体 **Scorer（价值评分者）**，对每轮每条修改意见按其对最终目标的 **价值/贡献度** 打分并记录；分值不够高 = **不合格意见**；须继续检查直至提出足够高分值的合格意见。

### 1.5.1 Scorer 职责边界

| 属性 | 说明 |
|------|------|
| **输入** | 当轮 Tester（及可选人工）产出的候选 Issue |
| **输出** | `metadata.value_score`、`value_score_rationale`、`value_qualified`、`scored_at` |
| **唯一写分** | 仅 Scorer 写入 `value_score*`；Scheduler **不得**绕过评分分派 |
| **禁止** | 改 `assigned_executor`、改业务源码、批量关闭 Issue（除非配置允许将低分标 `wontfix`） |

实现参考：[templates/scorer_loop.pseudo.md](./templates/scorer_loop.pseudo.md)、量表 [templates/scorer_rubric.md](./templates/scorer_rubric.md)。

### 1.5.2 打分流程

```
Tester 结束当轮 → Scorer 拉取 discovery_round_id 候选
    → 按 Rubric 对 North Star 五维加权 → value_score
    → value_qualified = (score >= min_value_score) ∧ 对齐闸门通过
    → 写入 Store + reports/value_scores.jsonl
    → 若 合格数 < min_qualified_per_round → 触发 §1.4.2 加深检查
```

### 1.5.3 与 Scheduler / Executor 的衔接

- **L1**：Scorer + Tester + 报告；人工处理高分 Issue  
- **L2+**：Scheduler **仅**对 `value_qualified == true` 的 Issue 做 `assign`  
- **Executor**：完成后可由 Scorer **复评**（可选）验证修复是否提升贡献度；复评不及格则 Verifier 打回  

### 1.5.4 低分与背离

| 情况 | `value_score` | `value_qualified` |
|------|---------------|-------------------|
| 高价值缺陷/改进 | ≥ 合格线 | `true` |
| 勉强相关、含糊 | 40–59 | `false` → 加深 |
| 背离 North Star | ≤ 20 | `false` + `goal_misaligned` |

---

## 1.6 外部触达预算（Prerequisite: External Touch Budget）

> **前提四（强烈建议，外部依赖项目视为不可妥协）**：凡会调用 **第三方 SaaS / 付费 API / 账号风控敏感** 服务的 discovery channel，必须声明触达成本等级，并遵守 **最低间隔**；不得绑在高频默认 health 环路上「顺带」打 live 探针。

### 1.6.1 触达等级（touch_class）

| touch_class | 含义 | 典型间隔 | 示例 |
|-------------|------|----------|------|
| `local` | 本机进程/文件，无外部账号 | Tester 60–300s | `py_compile`、静态扫描、localhost HTTP |
| `dependency` | 自建依赖就绪，非用户账号 API | 分钟–小时 | DB ping、磁盘、本地 CLI `--version` |
| `external` | 第三方 live 调用或完整用户旅程 | **小时级**（配置 `min_interval_sec`） | OAuth `--test`、完整 E2E 上传、create-resource API |

每个 channel 在 `automation/config.json`（或等价）中标注 `touch_class`；`external` 须配置 `min_interval_sec`（可按 channel 覆盖，如 `browser_e2e`）。

### 1.6.2 分层健康检查（layered health）

避免单一 `/health` 同时承担 liveness 与 expensive readiness：

| 层级 | 目的 | 建议 |
|------|------|------|
| **Liveness** | 进程存活、路由可达 | 高频；**不含** external live auth |
| **Readiness** | 依赖可用 | 中频 |
| **Deep / external** | 真实账号/API 可用 | 低频；独立 channel 或 query 参数（如 `?probe=light`） |

Tester / Verifier 的**自动化默认**应使用 liveness；deep 探针仅在预算允许时运行。

### 1.6.3 节流与空轮

- 当 `external_touch_guard`（或等价）阻止本轮 E2E / live 探针时：写入 `reports/throttled_channels.jsonl`（channel、等待秒数、round_id）。
- 该轮若仅有 local/dependency 渠道结果且无新 defect：**不因「未跑 E2E」记为空轮**（§1.4.2）。
- §1.4.2 **加深检查** 优先级：元检查 / lint / static → local health → **最后** 才启用 external / 全量 E2E。

参考实现：[templates/reference/external_touch_guard.py](./templates/reference/external_touch_guard.py)。

---

## 2. 五角色模型（Five Roles）

```
                    ┌─────────────┐
                    │   Guardian   │  监督子进程、退避、快照
                    └──────┬──────┘
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
      ┌─────────┐    ┌───────────┐   ┌──────────────┐
      │ Tester  │───►│Issue Store│◄──│  Scheduler   │
      │(发现)   │    │ (台账)    │   │ (唯一分配写)  │
      └────┬────┘    └─────▲─────┘   └──────┬───────┘
           │               │ score           │
           ▼               │                 ▼
      ┌─────────┐──────────┘          ┌──────────────┐
      │ Scorer  │  value_score*      │  Executors   │
      │(价值评分)│  唯一写分者         │ fixer|improver│
      └─────────┘                     │   |verifier  │
                                      └──────────────┘
```

### 2.1 Tester（发现）

**职责**：只写 Issue（经 Store 去重），不直接改业务代码（除非项目显式允许 tester-side 修复）。

典型 **discovery channels**：

- **Health checks**：HTTP/TCP、gRPC health、依赖就绪探针
- **Unit / integration tests**：测试套件、契约校验脚本
- **Static analysis**：lint、类型检查、已知腐化/混淆模式扫描
- **Browser automation**：Playwright、Selenium 等端到端用户路径（须 **业务终态断言**，见 §5 与 ADOPTION Phase 5；`touch_class: external`）

输出字段见 `templates/issue_schema.json`：`severity`、`type`、`description`、`paths`、`fingerprint`、`metadata`。

**每轮义务**（§1.3–§1.5）：产出候选意见供 Scorer 评分；全绿时仍须写入 `improvement`。当轮须 ≥`min_qualified_per_round` 条 **高分合格** 意见，否则触发加深检查。

### 2.2 Scorer（价值评分者）

**职责**：对每条候选修改意见评定 **North Star 贡献度**，持久化分值并判定合格。

- 按 [scorer_rubric.md](./templates/scorer_rubric.md) 加权打分（默认 0–100）
- 写入 `value_score`、`value_score_rationale`、`value_qualified`、`scored_at`、`scorer_round_id`
- 当轮合格产出不足 → 写 `reports/low_value_rounds.jsonl` 并触发 Tester 加深（§1.4.2）
- **禁止** 分配任务、修改业务代码

运行模式：`--once`（单轮评分）或 `--loop`；由 Guardian 监督。

### 2.3 Scheduler（协调 / 冲突预防）

**职责**：系统中 **唯一的 assignment writer**。

- 读取 `status: open` 且 **`value_qualified == true`** 的 Issue（L2+；L1 可仅人工分配）
- 按 `severity` 与 `type` 路由到 Executor（如 `health` → fixer，`improvement` → improver）
- 检查 **executor cap**（每类执行者最大并发）
- 检查 **path conflict**（路径前缀重叠则跳过）
- 获取 **path lock** 后写入 `assigned_executor`、`lease_until`

**禁止**：多个 Scheduler 实例同时写；Executor 自行抢单改 `assigned_executor`。

### 2.4 Executors（并行有界执行）

**职责**：只处理 **已分配给自己** 且 lease 未过期的 Issue。

常见类型（可扩展）：

| Executor | 典型 issue `type` | 行为边界 |
|----------|-------------------|----------|
| **fixer** | health, test_failure, static | 文档化、watchlist、重排队；**不**自动还原大范围腐化 |
| **improver** | improvement | 小步改进、配置调优（需策略表） |
| **verifier** | verification | 复跑测试/探针，关闭或打回父 Issue |

执行完成后：`resolved` / `wontfix` / 重新 `open`（验证失败）。

### 2.5 Guardian（监督）

**职责**：不执行业务修复，管理 **Tester / Scorer / Scheduler / Executors** 子进程（或容器/任务）。

- 启动错峰（stagger）避免 thundering herd
- 子进程退出 → **exponential backoff** 重启
- 周期性写入 **report snapshot**（如 `latest_issues.md`）
- 可选：磁盘、日志轮转、告警 webhook

Guardian 是 **运维可靠性** 层，与 Scheduler 的 **业务协调** 层正交。

---

## 3. Issue 生命周期（Issue Lifecycle）

```
                    ┌──────────┐
         创建 ─────►│   open   │
                    └────┬─────┘
                         │ Scheduler.assign()
                         ▼
                    ┌──────────┐
                    │ assigned │◄── lease_until 未过期
                    └────┬─────┘
                         │ Executor 开始处理
                         ▼
                 ┌──────────────┐
                 │ in_progress  │（可选显式状态；也可 assigned 即表示进行中）
                 └──────┬───────┘
                        │
          ┌─────────────┼─────────────┐
          ▼             ▼             ▼
    ┌──────────┐  ┌──────────┐  ┌────────────┐
    │ resolved │  │ wontfix  │  │ duplicate  │  终态（terminal）
    └──────────┘  └──────────┘  └────────────┘
          │
          │ verification 失败
          ▼
       回到 open 或新建 verification 子 Issue
```

### 3.1 状态语义

| Status | 含义 |
|--------|------|
| `open` | 已记录，未分配或 lease 已过期可再分配 |
| `assigned` | Scheduler 已指定 Executor 与 lease |
| `in_progress` | Executor 已认领（可选） |
| `resolved` | 验证通过或执行者确认修复 |
| `wontfix` | 终态：不再自动处理（**不等于**「需人工」，见 `metadata.terminal_reason`） |
| `duplicate` | 与已有 fingerprint 重复关闭 |

**`wontfix` 与人工闸门**：

- `wontfix` **不隐含** 需要人工操作。
- 仅当 `metadata.terminal_reason == human_required` 和/或 `metadata.requires_human == true` 时，人类报告归入 **Needs human**。
- 其他 `terminal_reason`（`abandoned`、`goal_misaligned`、`duplicate`、`low_value` 等）归入 **Closed / abandoned**，避免报告噪音。

### 3.2 Fingerprint 去重

对 `(type, normalized_description, sorted_paths)` 做哈希。非终态 Issue 存在相同 fingerprint 时 **不重复创建**，避免 Tester 每轮刷爆 Store。

### 3.3 Verification 子任务

Fixer 对无法自动修复的项（如文件腐化）应：

1. 记入 watchlist / `metadata.executor_note`
2. 创建 `type: verification`、关联 `metadata.parent_issue`
3. 由 **verifier** 在条件满足后复测并关闭父项

---

## 4. 冲突预防（Conflict Prevention）

| 机制 | 说明 |
|------|------|
| **Single-writer Scheduler** | 仅 Scheduler 修改 `assigned_executor` 与 lease |
| **Store lock** | Issue Store 读写串行（如 `.store.lock`） |
| **Path locks** | 对 `paths[]` 中每个相对路径加锁后再分配/编辑 |
| **Task lease** | `lease_until` 超时后 Issue 可重新 open 或再分配 |
| **Executor caps** | 如 fixer≤2、improver≤1，防止资源耗尽 |
| **Path conflict detection** | 路径相等或父子目录重叠则跳过并行分配 |

**原则**：宁可 **跳过一轮调度**，也不允许两个 Executor 同时写同一文件。

---

## 5. 发现渠道（Discovery Channels）

| 渠道 | 适用 | Issue `type` 示例 | 注意 |
|------|------|-------------------|------|
| Health | 服务/API 存活 | `health` | `touch_class: local` 或 `dependency`；通常 **不 auto-fix** |
| Unit / legacy scripts | 仓库内测试入口 | `test_failure` | `local`；区分环境缺依赖与代码错误 |
| Static | lint、腐化标记、安全规则 | `static` | `local`；高置信度规则才可 auto-fix |
| Browser E2E | 关键用户旅程 | `browser_e2e` | `external`；须业务断言 + `metadata.e2e_outcome`；截图见 schema |
| Improvement | 性能、可维护性建议 | `improvement` | 低优先级，improver 处理 |
| Verification | 复验队列 | `verification` | 由 fixer/improver 衍生 |

**Browser E2E 业务断言（防假绿）**：

- **禁止** 仅以「到达某 DOM 步骤 / 出现弹窗」为 pass，当 UI 文案或状态类表明业务失败（错误 modal、`.status.error` 等）。
- 推荐 `metadata.e2e_outcome`：`pass` | `infra_fail` | `pipeline_fail` | `throttled`。
- `pipeline_fail` 时应附 `metadata.screenshot`。

**组合策略**：Tester 一轮内按配置顺序执行（先 health 再 static 再 tests 再 browser），失败不阻断后续渠道（记录多条 Issue）。`external` 渠道受 §1.6 预算约束。

---

## 6. 扩展与节制（Scaling）

### 6.1 间隔与退避（Intervals & Backoff）

- **Tester interval**：60–300s，视 CI 成本调整
- **Scheduler interval**：15–60s
- **Executor poll**：30–90s
- **Guardian backoff**：子进程崩溃后 5s → 10s → … → cap 300s

### 6.2 Human-in-the-loop（人机协作）

必须人工介入的典型场景：

- 大规模文件 **corruption** / 需 `git restore`
- **认证/密钥**、生产配置
- **架构级** 行为变更
- 低置信度 static 命中（误报率高）

推荐：`metadata.requires_human: true`，Scheduler 路由到「仅文档化」策略。

### 6.3 何时 **不** 自动修复（When NOT to Auto-Fix）

| 条件 | 动作 |
|------|------|
| Issue `type: health` 且服务未启动 | `complete(resolved=false)` + note |
| 修改影响 >N 文件或 >M 行 | 仅创建 improvement Issue |
| 无测试覆盖的 critical 路径 | verifier 通过前禁止 auto-merge |
| 生产环境探针 | 只读发现，执行者在 staging |

LessonVerse 中 fixer 对 `static` 仅写 **corruption_watchlist**，即此原则的实践。

---

## 7. 可移植性（Portability）

本方法论 **与语言无关**：

- Issue Store：JSON、SQLite、PostgreSQL 均可
- Locks：文件锁、Redis、etcd
- Executors：Shell、Python、Node、Go 或 **调用外部 Agent API**

### 7.1 与 CI/CD 的关系（可选映射）

| Qualoop | CI/CD 类比 |
|--------------------|------------|
| Tester 一轮 | pipeline `test` stage |
| Issue Store | 缺陷平台 / GitHub Issues（可同步） |
| Scheduler | 队列 / 工单分配器 |
| Executor | 自动修复 bot / `workflow_dispatch` |
| Guardian | self-hosted runner supervisor |

**建议**：CI 负责 **门禁（merge blocking）**；Qualoop 负责 **长运行发现与本地/预发环境持续改进**。二者通过同一测试命令与 health URL 对齐。

---

## 8. 成熟度模型（Maturity Levels）

| 级别 | 名称 | 能力 |
|------|------|------|
| **L0** | Manual | 无自动化；人工 issue 跟踪 |
| **L1** | Observe | Tester + **Scorer** + Issue Store + 报告；人工修复 |
| **L2** | Coordinate | + Scheduler、locks、leases（仅分派 `value_qualified`） |
| **L3** | Bounded execute | + fixer/verifier；明确 auto-fix 边界 |
| **L4** | Continuous autonomous improvement | + improver、brain/LLM 桥接、与 CI 双向同步、指标驱动调参 |

**采纳建议**：大多数团队应先稳定 **L1–L2** 再开启 Executor 自动改代码。

---

## 9. 指标（Metrics）

| 指标 | 定义 | 用途 |
|------|------|------|
| **MTTR** | Issue `open` → `resolved` 中位时间 | 响应速度 |
| **Issue backlog** | 非终态 Issue 数量按 severity 加权 | 健康度 |
| **False positive rate** | 人工标为 `wontfix` 或 duplicate / 总创建数 | 调优 Tester 规则 |
| **Executor utilization** | assigned 数 / cap | 容量规划 |
| **Lease expiry rate** | lease 过期再分配次数 | 执行者过慢或卡死 |
| **Discovery coverage** | 各 channel 每轮命中数 | 补盲 spot |
| **Empty round rate** | 合格产出数 = 0 的 Tester 轮数 / 总轮数 | 检查深度是否不足 |
| **Low-value round rate** | 有候选但 `value_qualified` 数 < `min_qualified_per_round` / 总轮数 | 意见质量是否不足 |
| **Round mean value score** | 当轮全部候选 `value_score` 均值 | 整体贡献度趋势 |
| **Goal-misaligned change rate** | 标 `goal_misaligned` 或 verifier 以背离目标打回数 / 当轮关闭变更数 | 意见是否背离 North Star |

---

## 10. 与 LessonVerse 的关系

LessonVerse 在 `lessonverse/automation/` 实现了本方法论的一个 **Python 参考实例**（Guardian、Tester、Scheduler、fixer/improver/verifier、Playwright browser_e2e）。

- **不耦合**：本仓库无 LessonVerse 代码依赖
- **案例研究**：见 [case-study/LESSONVERSE.md](./case-study/LESSONVERSE.md) — 诚实列出 `issues.json` 中 **检测到** 与 **实际修复** 的差异

---

## 附录 A：最小配置项

见 `templates/config.example.json`：`intervals_seconds`、`executors.*.max_concurrent`、`scheduler.default_lease_minutes`、`guardian.*_backoff_seconds`。

## 附录 B：参考实现清单（采纳时）

1. `issue_store` — 单写锁 + fingerprint
2. `locks` — path_lock + store_lock
3. `tester` — 多渠道探测
4. `scorer` — 价值评分 + 合格判定
5. `scheduler` — 路由 + cap + conflict
6. `executors/*` — 有界处理
7. `guardian` — 进程监督
8. `reports` — 人类可读快照 + `value_scores.jsonl`

详细架构见 [ARCHITECTURE.md](./ARCHITECTURE.md)，落地步骤见 [ADOPTION_GUIDE.md](./ADOPTION_GUIDE.md)。
