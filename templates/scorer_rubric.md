# 价值评分量表（Scorer Rubric）

供 **Scorer（价值评分者）** 对每一轮每条修改意见打分。默认量程 **0–100**；`config.scorer.min_value_score` 为合格线（建议起步 **60**，成熟团队 **70**）。

## 评分原则

- 只评 **对 North Star 的贡献度**，不评实现难度或个人偏好  
- 与 [DEVELOPMENT_GOALS.md](../DEVELOPMENT_GOALS.md) 前提一、前提三一致；背离目标的意见 **≤20 分** 且 `value_qualified: false`  
- 须有 `value_score_rationale`（1–3 句，指向具体 North Star 条目与可验证信号）  

## 维度与权重（满分 100）

| 维度 | 权重 | 高分（8–10/10） | 低分（0–3/10） |
|------|------|-----------------|----------------|
| **可观测** | 25% | 明确进入 Store/指标，减少盲区或误报 | 模糊、不可追踪、重复刷屏 |
| **可协调** | 20% | 尊重 lock/lease/cap，不引发并行写冲突 | 扩大冲突面、绕过 Scheduler |
| **可验证** | 25% | 给出可复跑 channel 与通过标准 | 无法复验、纯主观重构 |
| **有节制** | 15% | 策略表内、范围小、可回滚 | 无界 auto-fix、触及禁止列表 |
| **可持续** | 15% | 巩固长运行与自动化健康 | 一次性脚本、削弱 Guardian/Tester |

各维度先打 0–10 分，再按权重合成 `value_score`（四舍五入整数）。

## 合格判定

```
value_qualified = (value_score >= min_value_score)
              AND (NOT goal_misaligned)
              AND (goal_alignment_note 非空)
```

## 典型分值锚点

| 分值区间 | 含义 | 当轮处理 |
|----------|------|----------|
| **80–100** | 高价值：关键缺陷或高杠杆改进 | 计入合格产出；Scheduler 可优先分配 |
| **60–79** | 合格：明确贡献 | 计入合格产出 |
| **40–59** | 低价值：勉强相关 | **不合格**；Tester 须加深检查或提出更好意见 |
| **0–39** | 无效/背离 | **不合格**；记 `reports/rejected_suggestions.jsonl` 或 `goal_misaligned` |

## 当轮合格（与 §1.4 合取）

```
当轮合格产出数 = count(本 round 新建/更新 Issue 且 value_qualified == true)
要求：当轮合格产出数 ≥ config.scorer.min_qualified_per_round  （默认 1）
```

若不满足：与 **空轮** 同等处理——加深检查，直至出现足够高分值的意见。
