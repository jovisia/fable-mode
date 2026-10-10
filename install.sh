#!/usr/bin/env bash
# Install the fable-mode skill family + agents into Claude Code (user scope).
# Skills -> ~/.claude/skills/<name>/SKILL.md ; agents -> ~/.claude/agents/<name>.md
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
SK="${CLAUDE_HOME:-$HOME/.claude}/skills"; AG="${CLAUDE_HOME:-$HOME/.claude}/agents"
mkdir -p "$SK/fable-mode" "$AG"
cp "$HERE/SKILL.md" "$SK/fable-mode/SKILL.md"
# fable-fable is superseded (v5) and no longer installed — see SUPERSEDED.md.
for n in fable-opus fable-sonnet fable-haiku execution-guardrails double-check; do
  mkdir -p "$SK/$n" && cp "$HERE/$n/SKILL.md" "$SK/$n/SKILL.md"
done
# Agent definitions go to agents/, never to skills/ — see README.
# Still installed because fable-haiku (v3 router) uses fable-worker-haiku.
cp "$HERE"/agents/*.md "$AG/"
echo "Installed skills:"; ls "$SK" | grep -E '^(fable-.*|execution-guardrails|double-check)$'
echo "Installed agents:"; ls "$AG" | grep '^fable-'
echo "Folder names match each SKILL.md 'name:' field — required for triggering."
