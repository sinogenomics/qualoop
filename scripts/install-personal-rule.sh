#!/usr/bin/env bash
# Install Qualoop personal AI rule into user-level config (one-time).
#
# Usage:
#   bash <(curl -fsSL https://raw.githubusercontent.com/sinogenomics/qualoop/main/scripts/install-personal-rule.sh) <tool>
#   # or
#   curl -fsSL https://raw.githubusercontent.com/sinogenomics/qualoop/main/scripts/install-personal-rule.sh | bash -s -- <tool>
#
# <tool> is one of:
#   claude   -> ~/.claude/CLAUDE.md            (Claude Code)
#   codex    -> ~/.codex/AGENTS.md             (Codex CLI)
#   gemini   -> ~/.gemini/GEMINI.md            (Gemini CLI)
#   cursor   -> ~/.cursor/rules/qualoop.mdc    (Cursor user rule, alwaysApply)
#   all      -> all of the above
#
# Idempotent: re-running upgrades the rule block in place without
# touching the rest of the file. Wrapped in BEGIN/END markers so it
# can be safely removed.

set -euo pipefail

TOOL="${1:-}"
if [[ -z "$TOOL" ]]; then
  cat >&2 <<EOF
Usage: $0 <claude|codex|gemini|cursor|all>

Examples:
  $0 claude
  $0 all
EOF
  exit 2
fi

RAW_URL="${QUALOOP_RAW_URL:-https://raw.githubusercontent.com/sinogenomics/qualoop/main/templates/personal/qualoop.personal-rule.md}"

need() { command -v "$1" >/dev/null 2>&1 || { echo "ERROR: '$1' is required" >&2; exit 4; }; }
need curl
need awk

TMP="$(mktemp)"
BLOCK="$(mktemp)"
trap 'rm -f "$TMP" "$BLOCK" "$TMP.new"' EXIT

echo "Fetching personal rule from:"
echo "  $RAW_URL"
curl -fsSL "$RAW_URL" -o "$TMP"

# Extract the section between the two '====' separator lines.
awk '/^====$/{flag=!flag; next} flag' "$TMP" > "$BLOCK"
if [[ ! -s "$BLOCK" ]]; then
  echo "ERROR: failed to extract personal rule block (no ==== ... ==== section found)." >&2
  exit 3
fi

BEGIN_TAG="<!-- BEGIN Qualoop personal rule -->"
END_TAG="<!-- END Qualoop personal rule -->"

write_block() {
  local file="$1"
  local kind="${2:-plain}"   # plain | mdc
  local dir
  dir="$(dirname "$file")"
  mkdir -p "$dir"
  [[ -f "$file" ]] || : > "$file"

  # 1) Strip any previous Qualoop block (idempotent upgrade).
  if grep -qF "$BEGIN_TAG" "$file"; then
    awk -v b="$BEGIN_TAG" -v e="$END_TAG" '
      $0==b {flag=1; next}
      $0==e {flag=0; next}
      !flag {print}
    ' "$file" > "$TMP.new"
    mv "$TMP.new" "$file"
  fi

  # 2) For Cursor .mdc, ensure frontmatter exists at the top.
  if [[ "$kind" == "mdc" ]]; then
    if ! head -n 1 "$file" 2>/dev/null | grep -q '^---$'; then
      {
        printf -- "---\n"
        printf "description: Qualoop personal rule (global)\n"
        printf "alwaysApply: true\n"
        printf -- "---\n\n"
        cat "$file"
      } > "$TMP.new"
      mv "$TMP.new" "$file"
    fi
  fi

  # 3) Append the new block.
  {
    printf "\n%s\n" "$BEGIN_TAG"
    cat "$BLOCK"
    printf "%s\n" "$END_TAG"
  } >> "$file"

  echo "  installed -> $file"
}

case "$TOOL" in
  claude) write_block "$HOME/.claude/CLAUDE.md"  plain ;;
  codex)  write_block "$HOME/.codex/AGENTS.md"   plain ;;
  gemini) write_block "$HOME/.gemini/GEMINI.md"  plain ;;
  cursor) write_block "$HOME/.cursor/rules/qualoop.mdc" mdc ;;
  all)
    write_block "$HOME/.claude/CLAUDE.md"  plain
    write_block "$HOME/.codex/AGENTS.md"   plain
    write_block "$HOME/.gemini/GEMINI.md"  plain
    write_block "$HOME/.cursor/rules/qualoop.mdc" mdc
    ;;
  *)
    echo "Unknown tool: $TOOL (use claude|codex|gemini|cursor|all)" >&2
    exit 2
    ;;
esac

cat <<'NEXT'

OK: Qualoop personal rule installed.

Next, in ANY new project, just say:

  Qualoop 接入, 开发目标见 docs/GOALS.md

(replace docs/GOALS.md with your project's actual goal document)

To uninstall later:
  Open the file shown above and remove everything between
  <!-- BEGIN Qualoop personal rule --> and <!-- END Qualoop personal rule -->
NEXT
