#!/usr/bin/env bash
set -euo pipefail

# Install the signal-scout skill for Claude Code (~/.claude/skills/) and
# Codex (~/.agents/skills/). OpenCode reads both.
# Usage: ./install.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Installing signal-scout..."

for SKILLS_DIR in "${HOME}/.claude/skills" "${HOME}/.agents/skills"; do
  mkdir -p "${SKILLS_DIR}/signal-scout"
  cp -r "${SCRIPT_DIR}/skills/signal-scout/"* "${SKILLS_DIR}/signal-scout/"
  echo "Installed: ${SKILLS_DIR}/signal-scout/"
done
echo "Available in Claude Code and OpenCode as /signal-scout"
