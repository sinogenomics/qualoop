#!/usr/bin/env bash
# Install Qualoop tool-agnostic AI contract into a business project (one-time).
#
# Works for any AI tool: Codex CLI, Cursor, Claude Code, Gemini CLI, Aider, Amp, etc.
#
# The North Star block in AGENTS.md is filled from ONE of:
#   --north-star "string"       : a single-line goal
#   --north-star-file <path>    : embed the whole file as the North Star
#   --north-star-file <path> --link-only : link to it, do not embed
# If none is given, the placeholder remains.
#
# Examples:
#   scripts/install-agents.sh --target . --north-star "make X reliable in Y"
#   scripts/install-agents.sh --target . --north-star-file docs/GOALS.md
#   scripts/install-agents.sh --target . --north-star-file docs/GOALS.md --link-only

set -euo pipefail

TARGET=""
NORTH_STAR=""
NORTH_STAR_FILE=""
LINK_ONLY=0
METH_REPO="https://github.com/sinogenomics/qualoop.git"
METH_REL="tools/qualoop"
DO_SUBMODULE=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target) TARGET="$2"; shift 2 ;;
    --north-star) NORTH_STAR="$2"; shift 2 ;;
    --north-star-file) NORTH_STAR_FILE="$2"; shift 2 ;;
    --link-only) LINK_ONLY=1; shift ;;
    --methodology-repo) METH_REPO="$2"; shift 2 ;;
    --methodology-path) METH_REL="$2"; shift 2 ;;
    --submodule) DO_SUBMODULE=1; shift ;;
    -h|--help)
      sed -n '1,20p' "$0"
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
if [[ -n "$NORTH_STAR" && -n "$NORTH_STAR_FILE" ]]; then
  echo "ERROR: pass only ONE of --north-star or --north-star-file" >&2
  exit 2
fi

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$HERE/.." && pwd)"
TARGET="$(cd "$TARGET" && pwd)"

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

AGENTS_SRC="$REPO_ROOT/templates/AGENTS.md"
AGENTS_DST="$TARGET/AGENTS.md"

# Build header (if any) and prepend to AGENTS.md
HEADER_FILE="$(mktemp)"
: > "$HEADER_FILE"

if [[ -n "$NORTH_STAR" ]]; then
  {
    echo "# North Star (from installer)"
    echo
    echo "> Source: provided as a string at install time."
    echo
    echo "- $NORTH_STAR"
    echo
    echo "---"
    echo
  } > "$HEADER_FILE"
elif [[ -n "$NORTH_STAR_FILE" ]]; then
  if [[ ! -f "$NORTH_STAR_FILE" ]]; then
    echo "ERROR: --north-star-file not found: $NORTH_STAR_FILE" >&2
    exit 2
  fi
  NS_ABS="$(cd "$(dirname "$NORTH_STAR_FILE")" && pwd)/$(basename "$NORTH_STAR_FILE")"
  case "$NS_ABS" in
    "$TARGET"/*)
      NS_REL="${NS_ABS#$TARGET/}"
      ;;
    *)
      cp -f "$NS_ABS" "$TARGET/NORTH_STAR.md"
      NS_REL="NORTH_STAR.md"
      echo "North Star source is outside the project; copied to: NORTH_STAR.md"
      ;;
  esac

  if [[ "$LINK_ONLY" -eq 1 ]]; then
    {
      echo "# North Star (from installer)"
      echo
      echo "> Source: see [\`$NS_REL\`](./$NS_REL) (single source of truth, not embedded)."
      echo "> AI agents MUST read that file before producing any opinion this round."
      echo
      echo "@$NS_REL"
      echo
      echo "---"
      echo
    } > "$HEADER_FILE"
  else
    {
      echo "# North Star (from installer)"
      echo
      echo "> Source: embedded copy of \`$NS_REL\` taken at install time."
      echo "> If the source file changes, re-run the installer (or edit this section in sync)."
      echo
      echo "<!-- BEGIN: embedded from $NS_REL -->"
      cat "$TARGET/$NS_REL"
      echo "<!-- END: embedded from $NS_REL -->"
      echo
      echo "---"
      echo
    } > "$HEADER_FILE"
  fi
fi

if [[ -s "$HEADER_FILE" ]]; then
  cat "$HEADER_FILE" "$AGENTS_SRC" > "$AGENTS_DST"
else
  cp -f "$AGENTS_SRC" "$AGENTS_DST"
fi
rm -f "$HEADER_FILE"

cp -f "$REPO_ROOT/templates/CLAUDE.md" "$TARGET/CLAUDE.md"
cp -f "$REPO_ROOT/templates/GEMINI.md" "$TARGET/GEMINI.md"

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
