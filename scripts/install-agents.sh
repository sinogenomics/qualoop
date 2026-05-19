#!/usr/bin/env bash
# Install Qualoop tool-agnostic AI contract into a business project (one-time).
#
# Works for any AI tool: Codex CLI, Cursor, Claude Code, Gemini CLI, Aider, Amp, etc.
#
# Usage:
#   scripts/install-agents.sh --target /path/to/your-app \
#       [--north-star "your one-line goal"] \
#       [--submodule] \
#       [--methodology-repo URL] \
#       [--methodology-path tools/qualoop]

set -euo pipefail

TARGET=""
NORTH_STAR=""
METH_REPO="https://github.com/sinogenomics/qualoop.git"
METH_REL="tools/qualoop"
DO_SUBMODULE=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target) TARGET="$2"; shift 2 ;;
    --north-star) NORTH_STAR="$2"; shift 2 ;;
    --methodology-repo) METH_REPO="$2"; shift 2 ;;
    --methodology-path) METH_REL="$2"; shift 2 ;;
    --submodule) DO_SUBMODULE=1; shift ;;
    -h|--help)
      sed -n '1,15p' "$0"
      exit 0
      ;;
    *)
      echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done

if [[ -z "$TARGET" ]]; then
  echo "ERROR: --target <path> is required" >&2
  exit 2
fi
if [[ ! -d "$TARGET" ]]; then
  echo "ERROR: target does not exist: $TARGET" >&2
  exit 2
fi

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$HERE/.." && pwd)"
TARGET="$(cd "$TARGET" && pwd)"

# 1) submodule (optional)
if [[ "$DO_SUBMODULE" -eq 1 ]]; then
  if [[ ! -d "$TARGET/.git" ]]; then
    echo "ERROR: target is not a git repo: $TARGET" >&2
    exit 2
  fi
  if [[ -e "$TARGET/$METH_REL" ]]; then
    echo "submodule path already exists, skipping: $TARGET/$METH_REL"
  else
    ( cd "$TARGET" && git submodule add "$METH_REPO" "$METH_REL" && git submodule update --init --recursive )
  fi
fi

# 2) AGENTS.md with optional North Star injection
AGENTS_SRC="$REPO_ROOT/templates/AGENTS.md"
AGENTS_DST="$TARGET/AGENTS.md"

if [[ -n "$NORTH_STAR" ]]; then
  python3 - "$AGENTS_SRC" "$AGENTS_DST" "$NORTH_STAR" <<'PY'
import re, sys
src, dst, ns = sys.argv[1], sys.argv[2], sys.argv[3]
with open(src, "r", encoding="utf-8") as f:
    text = f.read()
inj = (
    "<!-- NORTH_STAR_BEGIN -->\n"
    "**本项目的 North Star：**\n\n"
    f"- {ns}\n\n"
    "<!-- NORTH_STAR_END -->"
)
text = re.sub(r"<!-- NORTH_STAR_BEGIN -->.*?<!-- NORTH_STAR_END -->", inj, text, flags=re.S)
with open(dst, "w", encoding="utf-8") as f:
    f.write(text)
PY
else
  cp -f "$AGENTS_SRC" "$AGENTS_DST"
fi

# 3) CLAUDE.md / GEMINI.md
cp -f "$REPO_ROOT/templates/CLAUDE.md" "$TARGET/CLAUDE.md"
cp -f "$REPO_ROOT/templates/GEMINI.md" "$TARGET/GEMINI.md"

# 4) qualoop.json (project-root shared config) — only if not present
QJSON="$TARGET/qualoop.json"
if [[ ! -f "$QJSON" ]]; then
  cat > "$QJSON" <<JSON
{
  "methodologyRoot": "$METH_REL",
  "minValueScore": 60,
  "minQualifiedPerRound": 1,
  "maturity": "L1"
}
JSON
fi

echo
echo "OK: Qualoop AI contract installed into:"
echo "  $TARGET"
echo "Files:"
echo "  - AGENTS.md       (authoritative contract for all AI tools)"
echo "  - CLAUDE.md       (one-line include -> AGENTS.md)"
echo "  - GEMINI.md       (one-line include -> AGENTS.md)"
echo "  - qualoop.json    (shared config)"
echo
echo "Next: open the project in your AI tool of choice, then say:"
echo "  Qualoop 初始化"
echo "  (and provide the project's North Star if AGENTS.md still shows the placeholder)"
