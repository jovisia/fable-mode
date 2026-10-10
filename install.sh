#!/usr/bin/env bash
# Install the live fable-mode skill family (v6) into Claude Code (user scope).
# Skills -> ~/.claude/skills/<name>/SKILL.md
# fable-fable, fable-haiku and agents/ are retired and no longer installed — see
# SUPERSEDED.md. This script copies only; it never deletes an older install.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
SK="${CLAUDE_HOME:-$HOME/.claude}/skills"
mkdir -p "$SK/fable-mode"
cp "$HERE/SKILL.md" "$SK/fable-mode/SKILL.md"
for n in fable-opus fable-sonnet execution-guardrails double-check; do
  mkdir -p "$SK/$n" && cp "$HERE/$n/SKILL.md" "$SK/$n/SKILL.md"
done
echo "Installed skills:"; ls "$SK" | grep -E '^(fable-mode|fable-opus|fable-sonnet|execution-guardrails|double-check)$'
echo "Folder names match each SKILL.md 'name:' field — required for triggering."
