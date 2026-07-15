#!/usr/bin/env bash
set -euo pipefail

# Install the signal-scout skill into ~/.agents/skills/
# Usage: ./install.sh

SKILLS_DIR="${HOME}/.agents/skills"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Installing signal-scout..."

mkdir -p "${SKILLS_DIR}/signal-scout"
cp -r "${SCRIPT_DIR}/skills/signal-scout/"* "${SKILLS_DIR}/signal-scout/"

echo "Installed: ${SKILLS_DIR}/signal-scout/"
echo "Available in Claude Code and OpenCode as /signal-scout"
