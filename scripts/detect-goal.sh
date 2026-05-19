#!/usr/bin/env bash
# detect-goal.sh — Help an AI agent self-check whether the user's
# message contains a Qualoop project goal (North Star), and in which form.
#
# Usage:
#   bash detect-goal.sh "<the user's full message verbatim>"
#   echo "<the user's full message>" | bash detect-goal.sh
#
# One-liner (no checkout needed):
#   bash <(curl -fsSL https://raw.githubusercontent.com/sinogenomics/qualoop/main/scripts/detect-goal.sh) "<message>"
#
# Output (key=value, one per line):
#   MODE=file        # the user gave a path to a goal document
#     PATH=<path>
#     EXISTS=yes|no
#     NEARBY=<comma-separated candidates>  (only if EXISTS=no)
#
#   MODE=oneliner    # the user gave a natural-language goal
#     ONELINER=<text>
#
#   MODE=missing     # the user only gave the URL, no goal yet
#     ASK=ask the user once: file path or one-line goal?
#
# Exit code:
#   0 = MODE detected (any of the three above)
#   2 = invalid invocation
#
# The detection rules mirror AI-START-HERE.md STEP 0. This script is
# advisory; the AI agent is free to override based on richer context.

set -euo pipefail

MSG="${1:-}"
if [[ -z "$MSG" ]] && [[ ! -t 0 ]]; then
  MSG="$(cat)"
fi
if [[ -z "$MSG" ]]; then
  echo "Usage: $0 \"<user message>\"" >&2
  exit 2
fi

# 1) Strip Qualoop URLs (any github.com/.../qualoop or raw subdomain reference)
STRIPPED="$(printf '%s' "$MSG" | sed -E '
  s#https?://(raw\.)?github(usercontent)?\.com/[A-Za-z0-9_./-]*qualoop[A-Za-z0-9_./-]*##gi;
  s#https?://github\.com/sinogenomics/qualoop(\.git)?##gi;
')"

# 2) Find path-like candidates in the stripped message.
#    A token counts as a path candidate if any of:
#      - contains '/' or '\'
#      - ends with a known doc extension (.md .txt .rst .pdf .docx .json .yaml .yml)
#      - is preceded by Chinese/English cue: 见 / 目标见 / 需求文档 / per / see
EXTS='(\.md|\.txt|\.rst|\.pdf|\.docx|\.json|\.ya?ml)'
PATH_TOKEN_RE="[A-Za-z0-9_./\\:-]+($EXTS|/[A-Za-z0-9_./\\-]+)"

CANDIDATES_RAW="$(printf '%s\n' "$STRIPPED" \
  | grep -oE "$PATH_TOKEN_RE" 2>/dev/null || true)"

CANDIDATES="$(printf '%s\n' "$CANDIDATES_RAW" \
  | awk 'NF' \
  | awk '!seen[$0]++' \
  | grep -vE '^(https?:|git@)' || true)"

# 3) Score candidates by goal-likeness (filename matches GOAL|目标|需求|...)
score_candidate() {
  local p="$1"
  local base
  base="$(basename "$p")"
  local s=0
  if printf '%s' "$base" | grep -qiE 'GOAL|OBJECTIVE|REQUIREMENT|PRD|SPEC|NORTH[_-]?STAR'; then s=$((s+10)); fi
  if printf '%s' "$base" | grep -qE '目标|需求|说明书|规格'; then s=$((s+10)); fi
  if printf '%s' "$base" | grep -qE "$EXTS"; then s=$((s+3)); fi
  echo "$s"
}

BEST=""
BEST_SCORE=-1
while IFS= read -r p; do
  [[ -z "$p" ]] && continue
  sc=$(score_candidate "$p")
  if (( sc > BEST_SCORE )); then BEST_SCORE=$sc; BEST="$p"; fi
done <<<"$CANDIDATES"

if [[ -n "$BEST" ]]; then
  if [[ -f "$BEST" ]]; then
    echo "MODE=file"
    echo "PATH=$BEST"
    echo "EXISTS=yes"
    exit 0
  else
    # File path was named but does not exist on disk → suggest near-by
    NEARBY="$(ls -1 2>/dev/null \
      | grep -iE 'GOAL|目标|需求|OBJECTIVE|REQUIREMENT|PRD|SPEC|NORTH[_-]?STAR' \
      | head -n 5 | paste -sd ',' -)"
    echo "MODE=file"
    echo "PATH=$BEST"
    echo "EXISTS=no"
    echo "NEARBY=${NEARBY:-}"
    exit 0
  fi
fi

# 4) No path candidate. If there is any substantial non-URL text left,
#    treat it as a one-liner goal.
LEFTOVER="$(printf '%s' "$STRIPPED" \
  | sed -E 's#https?://[^[:space:]]+##g' \
  | tr -s '[:space:]' ' ' \
  | sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//')"
WORDS=$(printf '%s' "$LEFTOVER" | wc -w | tr -d ' ')

if (( WORDS >= 3 )); then
  echo "MODE=oneliner"
  echo "ONELINER=$LEFTOVER"
  exit 0
fi

# 5) Otherwise the message only had the URL; ask the user once.
echo "MODE=missing"
echo "ASK=Ask the user once: provide a goal file path (e.g. docs/GOALS.md) OR a one-line goal sentence."
exit 0
