# Qualoop 架构

本文描述六角色（含 **Architect** 和 **Scorer**）之间的 **职责边界、数据流与锁模型**。实现语言无关；LessonVerse 使用 Python 标准库 + JSON 文件 Store。

---

## 1. 逻辑架构

```
┌─────────────────────────────────────────────────────────────────┐
│                         Guardian                                 │
│  • spawn / restart: planner, tester, scorer, scheduler, fixer,   │
│    improver, verifier                                            │
│  • exponential backoff on crash                                  │
│  • periodic report snapshot                                      │
└────────────────────────────┬────────────────────────────────────┘
                             │ supervises
     ┌───────────────────────┼───────────────────────┐
     ▼                       ▼                       ▼
┌─────────┐           ┌────────────┐          ┌───────────────┐
│Planner  │           │            │          │               │
│(Arch)   ├──────────►│            │◄─────────┤  Scheduler    │
└─────────┘  append   │Issue Store │  assign  │  single writer│
┌─────────┐           │ (JSON/DB)  │          │               │
│Tester   ├──────────►│            │          └──────┬────────┘
└────┬────┘           └──────▲─────┘                 │
     │                       │ score only            │
     ▼                       │                       ▼
┌─────────┐                  │                ┌──────────────┐
│Scorer   │──────────────────┘                │  Executors   │
└─────────┘                                   └──────────────┘
                                                     │
                                                     ▼
                                              ┌──────────────┐
                                              │ fixer|       │
                                              │ improver|    │
                                              │ verifier     │
                                              └──────────────┘
                                                     │
                                            path locks + store lock
```

---

## 2. 角色详解

### 2.0 Architect / Planner

| 属性 | 说明 |
|------|------|
| 输入 | `GOALS.md` / `DEVELOPMENT_GOALS.md` / 北极星目标 |
| 输出 | 架构方案/规划蓝图文档（如 `docs/ARCHITECTURE_SCHEME.md`）、里程碑候选 Issue（`type: architecture`） |
| 作用阶段 | 项目初始化、重大目标重构、首轮开发前置期 |
| 副作用 | 写入 Issue Store，供 Scorer 进行打分门槛校验，防盲目微调 |
| 运行模式 | `plan` 子命令或首轮前置流程自动加载 |

**LessonVerse 映射**：`planner.py` — `QualoopPlanner`、目标解析器、里程碑拆解生成器。

### 2.1 Tester

| 属性 | 说明 |
|------|------|
| 输入 | `config`（URL、间隔、开关、channels 列表与加深策略） |
| 输出 | 候选 Issue（去重后）；供 Scorer 评分 |
| 空轮/低分轮 | 写 `empty_rounds.jsonl` / 触发加深；直至 Scorer 判定足够合格意见 |
| 副作用 | 可选截图、日志；**默认不改**业务源码 |
| 运行模式 | `--once` 或 `--loop` |

**LessonVerse 映射**：`tester.py` — health probe、Python 腐化扫描、legacy scripts、`browser_e2e.py`。

### 2.2 Scorer

| 属性 | 说明 |
|------|------|
| 输入 | 当轮 `discovery_round_id` 候选 Issue、`scorer_rubric`、North Star |
| 输出 | `value_score`、`value_score_rationale`、`value_qualified` |
| 唯一写分 | 仅 Scorer 写 `value_score*` 字段 |
| 副作用 | `reports/value_scores.jsonl`、`low_value_rounds.jsonl` |
| 运行模式 | `--once` 或 `--loop` |

见 [scorer_loop.pseudo.md](./templates/scorer_loop.pseudo.md)。

### 2.3 Scheduler

| 属性 | 说明 |
|------|------|
| 输入 | open 且 `value_qualified` 的 Issues、assigned 计数、in-progress paths |
| 输出 | `assigned` + `lease_until` |
| 路由表 | `issue.type` → executor 名 |
| 约束 | cap、path conflict、path_lock 试探 |

**LessonVerse 映射**：`scheduler.py` — `_TYPE_ROUTING`、`_EXECUTOR_CAPS`、`dry_run` 模式。

### 2.4 Executors

共享模式（参考 `executors/base.py`）：

1. 列出 `assigned_executor == self` 且 lease 有效
2. **目标对齐闸门**：若无 `metadata.goal_alignment_note`（L3+ 且 `type: improvement` 时必填），则仅文档化或 `resolved=false`
3. `path_lock` 包裹实际文件操作
4. `complete_issue(resolved=..., note=...)` — note 须复述对齐理由
5. 可选 spawn verification Issue

每轮须满足 [METHODOLOGY.md](./METHODOLOGY.md) **§1.3–§1.5**：对齐、必有产出、**Scorer 分值达标**。详见 [DEVELOPMENT_GOALS.md](./DEVELOPMENT_GOALS.md) §零。

| Executor | 职责 | 不应做 |
|----------|------|--------|
| **Fixer** | 安全兜底、watchlist、health 说明 | 批量 git restore 无确认 |
| **Improver** | 配置/文档/小优化 | 无测试改核心算法 |
| **Verifier** | 重跑 probe/test | 扩大 scope 改无关文件 |

### 2.5 Guardian

| 属性 | 说明 |
|------|------|
| 监督对象 | 所有 `--loop` 子进程 |
| 健康检查 | `poll()` 非空则 backoff 重启 |
| 报告 | `report_snapshot` 间隔写 markdown |

**LessonVerse 映射**：`guardian.py` — `_AGENTS` 元组列表，`start.bat` 一键启动。

---

## 3. Issue Store

### 3.1 存储布局（推荐）

```
automation/
  issues.json          # 主 Store
  .store.lock          # Store 级互斥
  locks/
    path_app__py.lock  # 路径哈希锁
  logs/
  reports/
    latest_issues.md
    screenshots/
```

### 3.2 原子写

1. 写入 `issues.json.tmp`
2. `replace` 到 `issues.json`
3. 全程持有 `store_lock`

### 3.3 API 表面（概念）

- `add(severity, type, description, paths?, metadata?)` → issue | null（dedupe）
- `assign(id, executor, lease_until)`
- `update(id, **fields)`
- `list_issues(status_filter?)`

Schema：`templates/issue_schema.json`。

---

## 4. 锁与 Lease

### 4.1 Path lock

- 文件名：`path_<normalized_relative_path>.lock`
- 内容：持有进程 PID
- 陈旧锁：PID 不存在或 mtime > 1h 可抢占

### 4.2 Task lease

- Scheduler 分配时设置 `lease_until`（ISO8601 UTC）
- Executor 应在 lease 内完成；超时后 Scheduler 可将 Issue 重回 `open`（实现可选）

### 4.3 冲突检测算法（路径）

对两组路径 `A`、`B`：若存在 `a==b` 或 `a` 是 `b` 的子路径（或反之），则冲突。

---

## 5. 类型路由（可配置）

默认参考（与 LessonVerse 一致）：

| `issue.type` | Executor |
|--------------|----------|
| health | fixer |
| test_failure | fixer |
| static | fixer |
| improvement | improver |
| architecture | improver（或专用 executor） |
| verification | verifier |
| browser_e2e | fixer（或专用 executor） |

### 5.1 Verifier 策略（按 `issue.type`，L3 前必须选定）

| `issue.type` | L3 推荐策略 | 说明 |
|--------------|-------------|------|
| `health` | 复跑 **liveness** URL（非 deep external） | 与 §1.6 分层 health 一致 |
| `performance` | 复跑 `metadata.url`，prefer light probe | 避免 verifier 触发 external |
| `test_failure` / `static` | 复跑对应脚本或规则 | 范围不扩大 |
| `browser_e2e` | **A)** Verifier 复跑 E2E（受 `external_touch_guard`）**或** **B)** 禁止 auto-`resolved`，仅人工 + 截图 | 未实现 A 时不得静默积压 open |
| `improvement` | 一般不 verifier；人工采纳 | 建议仅 jsonl 不入执行队列 |
| `verification` | 父任务条件复测 | 见 METHODOLOGY §3.3 |

默认采用 **B** 直至项目实现受预算约束的 E2E 复跑（参考 `templates/reference/external_touch_guard.py`）。

---

## 6. 可观测性

| 产物 | 消费者 |
|------|--------|
| `logs/<role>_YYYYMMDD.log` | 运维 / 调试 |
| `reports/latest_issues.md` | 人类每日巡检 |
| `reports/screenshots/*.png` | E2E 失败分析 |
| `reports/throttled_channels.jsonl` | external 渠道被预算跳过时的审计 |
| `corruption_watchlist.txt` | 需 git 还原的文件列表 |

---

## 7. 扩展点

- **brain_bridge**：将 Issue 转为外部 LLM 项目任务（LessonVerse 默认关闭）
- **dev_log_sync**：`resolved` 时追加 JSON 活动流
- **CI webhook**：Tester 失败推送到 Slack；Scheduler 从 GitHub Issues 拉取

---

## 8. 部署拓扑

| 拓扑 | 说明 |
|------|------|
| 开发者本机 | Guardian + localhost 探针（LessonVerse 默认） |
| 共享 staging | 单 Guardian 实例；多开发者只读 reports |
| CI 仅 L1 | 无 Guardian；`tester --once` 作为 job step |

详见 [ADOPTION_GUIDE.md](./ADOPTION_GUIDE.md)。
