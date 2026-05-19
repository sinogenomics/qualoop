# Scorer 主循环（伪代码）

**价值评分者**：每轮 Tester 产出后，对候选修改意见打分；**唯一**写入 `value_score*` 字段的角色。

```
CONFIG ← load_config()
MIN_SCORE ← CONFIG.scorer.min_value_score          // e.g. 60
MIN_QUALIFIED ← CONFIG.scorer.min_qualified_per_round  // e.g. 1
RUBRIC ← load("templates/scorer_rubric.md")

function score_issue(issue, north_star):
  if issue.metadata.goal_misaligned:
    return { score: 0, qualified: false, rationale: "misaligned" }

  dims ← evaluate_dimensions(issue, RUBRIC, north_star)  // 可规则 + 可选 LLM
  score ← weighted_sum(dims)
  qualified ← score >= MIN_SCORE
              AND issue.metadata.goal_alignment_note is non-empty

  return { score, qualified, rationale: explain(dims), dims }

function process_round(round_id):
  candidates ← list_issues(
    metadata.discovery_round_id == round_id,
    status in ["open", "assigned"],   // 当轮新产出
    value_score is null OR needs_rescore
  )

  for issue in candidates:
    result ← score_issue(issue, north_star)
    under store_lock:
      issue.metadata.value_score ← result.score
      issue.metadata.value_score_rationale ← result.rationale
      issue.metadata.value_qualified ← result.qualified
      issue.metadata.scored_at ← now_utc()
      issue.metadata.scorer_round_id ← round_id
      if NOT result.qualified:
        issue.metadata.value_insufficient ← true
      persist(issue)

    append_jsonl("reports/value_scores.jsonl", {
      round_id, issue_id: issue.id, score: result.score,
      qualified: result.qualified, rationale: result.rationale
    })

  qualified_count ← count(candidates where value_qualified)
  if qualified_count < MIN_QUALIFIED:
    append_jsonl("reports/low_value_rounds.jsonl", {
      round_id, qualified_count, min_required: MIN_QUALIFIED
    })
    signal_tester_depth_escalation(round_id)  // 同 §1.4 加深检查

// --- loop ---
while true:
  round_id ← current_or_latest_tester_round()
  if round_id changed since last_scored:
    process_round(round_id)
  sleep(CONFIG.intervals_seconds.scorer)
```

**禁止**：Scorer 修改 `assigned_executor`、`status`（除团队显式允许将不合格标为 `wontfix`）、业务源码。  
**与 Scheduler 关系**：Scheduler **仅**分配 `value_qualified == true` 的 Issue（L2+）。
