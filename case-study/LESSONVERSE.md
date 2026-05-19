# 案例研究：LessonVerse

**来源**：`E:\20260502_MZH\lessonverse\automation\`（2026-05-18 快照）  
**数据**：`automation/issues.json`、`automation/reports/latest_issues.md`、`docs/DEV_PROCESS_LOG.md`

本案例 **诚实区分**：

- **Detected**：Tester/Scheduler 写入 Issue Store 的内容
- **Automation-fixed**：Executor 将 `status` 设为 `resolved` 或实质修复代码
- **Collaboration-fixed**：Cursor 智能体 / 人工根据反馈修改，**不一定**关闭 Issue

---

## 1. 实现映射

| 方法论角色 | LessonVerse 文件 |
|------------|------------------|
| Tester | `tester.py`, `browser_e2e.py` |
| Scheduler | `scheduler.py` |
| Executors | `executors/fixer.py`, `improver.py`, `verifier.py` |
| Guardian | `guardian.py`, `start.bat` |
| Issue Store | `issue_store.py`, `issues.json` |
| Locks | `locks.py`, `automation/locks/` |

架构说明：项目根 `AUTOMATION.md`。

---

## 2. Detected（自动化发现）

### 2.1 Health（环境）

| 时间 (UTC) | 描述 | 状态（快照时） |
|------------|------|----------------|
| 07:38 | 前端 `:8080` 连接被拒绝 | open |
| 07:38 | 后端 `:5000/api/health` 连接被拒绝 | open |
| 13:12 | 后端 health **HTTP 404** | open |
| 21:42+ | 日志显示 health **HTTP 200**（含 `notebooklm_auth_local` 等） | Issue 仍为 open；fixer note：需人工启服，未标 resolved |

### 2.2 Legacy 测试脚本（test_failure）

| 脚本 | 错误 |
|------|------|
| `automated_tester.py` | `ModuleNotFoundError: requests` |
| `e2e_test.py` | 第 25 行 `asstrt` 语法错误 |
| `api_contract_validator.py` | `os.path.exises` 拼写 / `ntpath` 无属性 |

每轮 Tester 可能产生 **重复指纹** 的变体（约 6 条 open）。

### 2.3 静态腐化（static）

Tester 扫描项目根 `*.py`，命中 rebranding/混淆标记（`return `、`python3` 等），**17+ 文件**，包括但不限于：

- `app.py`
- `ai_recommendations.py`, `api_contract_validator.py`
- `automated_tester.py`, `e2e_test.py`
- `auto_auth_monitor.py`, `refresh_auth.py`, `simple_refresh_auth.py`
- `continuous_improver.py`, `enhance_features.py`, `improvement_tracker.py`
- `intelligent_optimizer.py`, `quality_assessor.py`, `setup_i18n.py`
- `simple_e2e_test.py`, `system_reporter.py`, `ux_optimizer.py`
- `import_desktop_cookies.py`, **`notebooklm_cli.py`**

Fixer 对 `ai_recommendations.py`、`api_contract_validator.py`：**assigned** → 写入 `corruption_watchlist.txt`，并 spawn **verification** 子 Issue；**未还原文件**。

### 2.4 浏览器 E2E（browser_e2e）

| 时间 | 描述 |
|------|------|
| 13:58 UTC | Playwright `#auth-indicator` **strict mode violation**（DOM 内 2 个相同 id：页头 + 错误模态框） |
| 截图 | `automation/reports/screenshots/browser_e2e_exception_20260518T135828Z.png` |

E2E 流程设计：填项目名 → 上传 `automation/fixtures/sample.png` → 点击「开始生成」→ 检测步骤 2/错误模态/认证后步骤 3。

后续日志（~21:59 UTC）：能打开错误模态并显示认证过期文案，**未再新增** 同类 issue。

---

## 3. Automation-fixed（自动化直接修复）

**截至 2026-05-18 快照：`issues.json` 中无任何 `status: resolved`。**

Fixer **已执行但仍 open** 的行为：

| type | 动作 |
|------|------|
| health | `executor_note`: 需 :5000/:8080；**无 auto-fix** |
| static | corruption_watchlist + verification 子任务 |
| test_failure | 复验队列说明，**未修脚本** |

**结论**：本阶段自动化价值主要是 **持续发现、去重、分派、可观测性**，而非自动合并修复。

---

## 4. Collaboration-fixed（协作修复，非 resolved）

用户反馈或自动化线索触发，由 **Cursor 智能体** 等在 `lessonverse` 改代码（摘自 `docs/DEV_PROCESS_LOG.md`）：

| 问题域 | 现象 | 与自动化的关系 |
|--------|------|----------------|
| **选图/上传无反应** | 首页选照片无响应 | `script.js` 事件绑定/腐化；用户报告 |
| **开始生成无反应** | 「开始生成学习资料」无反馈 | `script.js` + `app.py` 路由 |
| **NotebookLM 本地登录** | 本机已登录但后端未识别 | 与 health/auth 探针一致；后期 auth OK |
| **生成链路空结果** | 能到步骤 2 但无材料 | subprocess / mock 排查 |
| **处理页跳回首页** | 3–5s 回到步骤 1，「AI服务未认证」 | auth 轮询；browser E2E 用于捕获回归 |
| **浏览器 E2E 能力** | 需本地操控浏览器 | **新增** `automation/browser_e2e.py`（方法论增强） |
| **`/api/health` 404→200** | 路由修复 | Tester 日志 Backend health OK |

`browser_e2e.py` 中 `_header_locator()` 针对 **重复 id** 的修复尝试（限定 `header.header #auth-indicator`），但 **issues.json 仍保留** 13:58 的 open 记录直至人工 resolved。

---

## 5. 仍开放（快照摘要）

约 **31** 条活跃 Issue（见 `latest_issues.md`）：

- health × 若干（含已恢复但 store 未关）
- test_failure × ~6
- static × ~17 + 2 assigned（仅文档化）
- verification × 2
- browser_e2e × 1（重复 `#auth-indicator`）

---

## 6. 教训（可迁移到其他项目）

1. **Issue Store 与真实修复脱节**：协作修复不会自动 `resolved` — 需 `dev_log_sync` 或人工关单。
2. **Health issue 不应 auto-fix**：避免 Executor 误启/误杀进程。
3. **Static 腐化需 git 还原策略**：fixer 只应 watchlist + verification。
4. **E2E 选择器**：模态框内勿复制与页头相同的 `id`；优先 `header #id` 或 `data-testid`。
5. **NotebookLM 路径**：`notebooklm_cli.py` 腐化影响本地认证链路 — 应纳入高优先级 static 规则。
6. **Upload / generate 流程**：用户路径问题由 E2E 覆盖；发现与修复分属 Tester vs 人工/Agent。

---

## 7. 引用方式

在其他文档中写：

> 参考 Qualoop 案例 [LessonVerse](./LESSONVERSE.md)；实现见 `lessonverse/automation/`，**非**本仓库依赖。
