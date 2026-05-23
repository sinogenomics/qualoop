## 自动化运行成果（机器生成）

_生成时间：2026-05-23T11:51:14+00:00 · 统计窗口：最近 10.0 小时_

### 摘要

| 指标 | 数量 | 说明 |
|------|------|------|
| 新入库问题 | 1 | 按 `created_at` 落在窗口内（指纹去重） |
| 自动化直接关闭 | 1 | `issues.json` 中 `resolved` 且归因自动化 |
| 人工/协作处理 | 0 | resolved 但 fixer 文档化或未改代码 |
| 仍开放 | 0 | open / assigned / in_progress |
| Tester 轮次 | 2 | 日志中 run started |
| 浏览器 E2E | 0 | 通过 0 / 失败 0 |
| Scheduler 分派（去重） | 0 | |
| Improver 建议 | 12 | `improvement_suggestions.jsonl` |
| 指标快照 | 0 | metrics 目录 |

### 新发现按类型

```json
{
  "compliance": 1
}
```

### 检查轮次（节选，最新优先）

- **2026-05-23 19:51 HKT** [deep] — 新入库 0；本轮检测 18 项（通过 13 / 警告 5 / 失败 0）；改进意见 1 条（目标对齐） （新入库 0 / 本轮检测 18 / 关 0 / 开放 0）
- **2026-05-23 19:51 HKT** [standard] — 新入库 0；本轮检测 16 项（通过 12 / 警告 4 / 失败 0）；改进意见 1 条（目标对齐） （新入库 0 / 本轮检测 16 / 关 0 / 开放 0）

完整 JSON：`automation/reports/automation_outcomes.json` · 开放问题列表：`automation/reports/latest_issues.md`
