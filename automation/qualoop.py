#!/usr/bin/env python3
import sys
import os
import argparse
from datetime import datetime

from automation.paths import load_config, get_abs_path
from automation.issue_store import IssueStore
from automation.tester import QualoopTester
from automation.scorer import QualoopScorer
from automation.reports import QualoopReporter
from automation.planner import QualoopPlanner

def cmd_plan(args):
    """Run Architect / Planner to generate overall planning scheme and milestone issues."""
    planner = QualoopPlanner(goals_path=args.goals, scheme_path=args.scheme)
    planner.run_planning()

def cmd_init(args):
    """Initialize the automation workspace directories and config."""
    print("Initializing Qualoop automation workspace...")
    config = load_config()
    
    # Initialize Issue Store
    store = IssueStore()
    store.save()
    
    # Ensure reports directory exists
    reports_dir = get_abs_path("automation/reports")
    os.makedirs(reports_dir, exist_ok=True)
    
    print("✅ Qualoop L1 Observe workspace initialized successfully.")
    print("Paths created:")
    print("  - automation/config.json")
    print("  - automation/issues.json")
    print("  - automation/reports/")

def cmd_check(args):
    """Run a full Qualoop round (Discover -> Score -> Report) with optional depth escalation."""
    deep_mode = args.deep
    round_id = f"pass_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
    print(f"Starting Qualoop check round: {round_id} (deep={deep_mode})...")

    config = load_config()
    min_qualified = config.get("scorer", {}).get("min_qualified_per_round", 1)

    # 1. Load Issue Store
    store = IssueStore()

    # 2. Run discovery (Tester)
    tester = QualoopTester(deep=deep_mode)
    candidates = tester.run_all_checks()

    # 3. Score candidates (Scorer)
    scorer = QualoopScorer()
    scored_issues = []
    
    # Temporary list to hold updated/created issue objects in the store
    session_issues = []
    active_fingerprints = set()

    for cand in candidates:
        # Check if already has a fingerprint to check if duplicates occur in candidate list
        fp = IssueStore.calculate_fingerprint(cand["type"], cand["description"], cand["paths"])
        if fp in active_fingerprints:
            continue
        active_fingerprints.add(fp)

        # Add to store first, then score
        issue = store.add_candidate(
            severity=cand["severity"],
            issue_type=cand["type"],
            description=cand["description"],
            paths=cand["paths"],
            metadata=cand["metadata"]
        )
        scorer.evaluate_and_score(issue, round_id)
        session_issues.append(issue)

    # Count qualified issues in the当轮 session
    qualified_count = sum(1 for issue in session_issues if issue.get("metadata", {}).get("value_qualified", False))

    # Prerequisite Two: Depth escalation if output count is insufficient
    if qualified_count < min_qualified and not deep_mode:
        print(f"⚠️ [Escalation] Low value round: found {qualified_count} qualified issue(s) (min required: {min_qualified}).")
        print("Escalating inspection depth: re-running discovery with deep checks enabled...")
        
        deep_mode = True
        tester = QualoopTester(deep=True)
        candidates = tester.run_all_checks()
        
        # Reset and score again
        session_issues = []
        active_fingerprints = set()
        for cand in candidates:
            fp = IssueStore.calculate_fingerprint(cand["type"], cand["description"], cand["paths"])
            if fp in active_fingerprints:
                continue
            active_fingerprints.add(fp)

            issue = store.add_candidate(
                severity=cand["severity"],
                issue_type=cand["type"],
                description=cand["description"],
                paths=cand["paths"],
                metadata=cand["metadata"]
            )
            scorer.evaluate_and_score(issue, round_id)
            session_issues.append(issue)

        qualified_count = sum(1 for issue in session_issues if issue.get("metadata", {}).get("value_qualified", False))

    # 4. Auto-resolve issues that are no longer detected
    resolved_count = store.resolve_missing(active_fingerprints)
    if resolved_count > 0:
        print(f"✨ Auto-resolved {resolved_count} issue(s) no longer detected by the tester.")

    # Save Issue Store
    store.save()

    # 5. Generate human-readable and machine-readable reports
    reporter = QualoopReporter(store.get_issues(), round_id)
    reporter.write_value_scores_log(session_issues)
    
    if qualified_count < min_qualified:
        # Log low value round audit
        reporter.write_low_value_log(qualified_count, min_required=min_qualified)

    report_path = reporter.generate_report()

    # Calculate statistics for console output
    max_score = 0
    min_score = 100
    for issue in session_issues:
        score = issue.get("metadata", {}).get("value_score", 0)
        if score > max_score:
            max_score = score
        if score < min_score:
            min_score = score
    if not session_issues:
        min_score = 0

    print("\n" + "="*50)
    print("🎉 Qualoop Check Round Complete!")
    print(f"Round ID:      {round_id}")
    print(f"Total Found:   {len(session_issues)} candidate(s)")
    print(f"Qualified:     {qualified_count} issue(s) (value_score >= 60)")
    print(f"Max Score:     {max_score}")
    print(f"Min Score:     {min_score}")
    print(f"Report path:   {report_path}")
    print("="*50 + "\n")

def main():
    parser = argparse.ArgumentParser(description="Qualoop CLI Automation Tool (L1)")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # init command
    subparsers.add_parser("init", help="Initialize the Qualoop automation workspace")

    # plan command
    plan_parser = subparsers.add_parser("plan", help="Run Architect / Planner to generate milestones")
    plan_parser.add_argument("--goals", help="Path to goal document (e.g. DEVELOPMENT_GOALS.md)")
    plan_parser.add_argument("--scheme", help="Target path for architecture scheme output file")

    # check command
    check_parser = subparsers.add_parser("check", help="Run discovery, scoring and reporting")
    check_parser.add_argument("--deep", action="store_true", help="Force depth escalation and run deep checks")

    args = parser.parse_args()

    if args.command == "init":
        cmd_init(args)
    elif args.command == "check":
        cmd_check(args)
    elif args.command == "plan":
        cmd_plan(args)

if __name__ == "__main__":
    main()
