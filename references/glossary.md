# 术语表（Glossary）

| 中文 | English | 定义 |
|------|---------|------|
| 质环 | Qualoop | 本项目品牌：持续自进化的质量闭环方法论（Qual + loop） |
| 发现者 | Tester | 运行探测渠道、向 Issue Store 追加候选意见的角色 |
| 价值评分者 | Scorer | 对每条修改意见按 North Star 贡献度打分；唯一写入 value_score* 的角色 |
| 价值分 | value_score | 0–100，表示意见对最终目标的贡献度 |
| 合格意见 | value_qualified | 分值 ≥ 合格线且通过对齐闸门；计入当轮合格产出 |
| 低分轮 | Low-value round | 有候选但合格产出数不足；须加深检查 |
| 调度器 | Scheduler | 唯一负责分配 Issue 给 Executor 的协调角色 |
| 执行者 | Executor | 处理已分配 Issue 的工作角色（fixer / improver / verifier） |
| 守护者 | Guardian | 监督 Tester/Scheduler/Executor 进程存活与退避重启 |
| 问题台账 | Issue Store | 持久化 Issue 列表及元数据（JSON/DB） |
| 问题 | Issue | 一条可跟踪的缺陷或改进项，含 severity、type、status、paths |
| 指纹 | Fingerprint | 用于去重的 Issue 哈希键 |
| 租约 | Task lease | `lease_until` 字段，分配有效期 |
| 路径锁 | Path lock | 文件级互斥，防止并行写同一资源 |
| 库锁 | Store lock | Issue Store 读写互斥 |
| 执行者上限 | Executor cap | 每类 Executor 最大并发 assigned 数 |
| 路径冲突 | Path conflict | 两 Issue 的 paths 重叠或父子包含 |
| 发现渠道 | Discovery channel | health / test / static / browser_e2e 等输入源 |
| 终态 | Terminal status | resolved / wontfix / duplicate |
| 开放态 | Open statuses | open / assigned / in_progress |
| 验证子任务 | Verification issue | fixer 无法完成时由 verifier 复验的派生 Issue |
| 有界修复 | Bounded fix | Executor 仅允许策略表内的安全操作 |
| 人机协作 | Human-in-the-loop | 需人工批准或执行的修复路径 |
| 目标对齐 | Goal alignment | 每轮修改意见须严谨、审慎，朝向 North Star，不背离（METHODOLOGY §1.3） |
| 每轮必有产出 | Mandatory round output | 每轮须 ≥1 条有效修改意见；无产出 = 深度不足（METHODOLOGY §1.4） |
| 有效产出 | Valid round output | 通过对齐闸门的 defect 或 improvement/optimization Issue |
| 空轮 | Empty round | 当轮有效产出数 = 0；须加深检查，不算合格轮次 |
| 检查加深 | Inspection depth escalation | 空轮后扩展 channel、范围或降阈值以强制产出 |
| 空轮率 | Empty round rate | 空轮数 / Tester 总轮数 |
| 目标对齐说明 | goal_alignment_note | Issue metadata：说明本条如何服务最终目标，L3+ improver 分配前建议必填 |
| 目标背离标记 | goal_misaligned | Issue metadata：该意见或变更因背离 North Star 被拒绝或打回 |
| 误导向变更率 | Goal-misaligned change rate | 因背离目标被打回或标 wontfix 的变更占当轮关闭变更的比例 |
| 成熟度 | Maturity level | L0–L4 采纳深度模型 |
| 平均修复时间 | MTTR | Mean time to resolve |
| 误报率 | False positive rate | 被标为 wontfix/duplicate 的比例 |
| 干跑 | Dry run | Scheduler 只日志不写入分配 |
| 快照报告 | Report snapshot | 如 latest_issues.md 的人类可读导出 |
| 浏览器端到端 | Browser E2E | Playwright 等真实 UI 流程测试 |
| 腐化扫描 | Corruption scan | 检测源码中已知混淆/损坏标记 |
| 退避 | Backoff | 进程崩溃后重启等待时间的指数增长 |
