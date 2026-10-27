#!/usr/bin/env node
"use strict";

const fs = require("fs");
const path = require("path");
const os = require("os");

const SKILL_NAME = "signal-scout";
const SOURCE_DIR = path.join(__dirname, "..", "skills", SKILL_NAME);

// Claude Code reads personal skills from ~/.claude/skills
// (https://code.claude.com/docs/en/skills); Codex reads user skills from
// ~/.agents/skills (https://learn.chatgpt.com/docs/build-skills). OpenCode
// reads both. Install only for tools present on this machine; if none is
// detected, default to Claude Code.
function parseTargetDirs(argv) {
  const flagIndex = argv.indexOf("--dir");
  if (flagIndex !== -1 && argv[flagIndex + 1]) {
    return [argv[flagIndex + 1]];
  }
  const home = os.homedir();
  const has = (...p) => fs.existsSync(path.join(home, ...p));
  const dirs = [];
  if (has(".claude")) dirs.push(path.join(home, ".claude", "skills", SKILL_NAME));
  if (has(".codex") || has(".agents") || has(".config", "opencode")) {
    dirs.push(path.join(home, ".agents", "skills", SKILL_NAME));
  }
  return dirs.length ? dirs : [path.join(home, ".claude", "skills", SKILL_NAME)];
}

function copyRecursive(src, dest) {
  const stat = fs.statSync(src);
  if (stat.isDirectory()) {
    fs.mkdirSync(dest, { recursive: true });
    for (const entry of fs.readdirSync(src)) {
      copyRecursive(path.join(src, entry), path.join(dest, entry));
    }
  } else {
    fs.copyFileSync(src, dest);
  }
}

function main() {
  const targetDirs = parseTargetDirs(process.argv.slice(2));

  if (!fs.existsSync(SOURCE_DIR)) {
    console.error(`Skill source not found at ${SOURCE_DIR}`);
    process.exit(1);
  }

  // Overwrite our files in place; never delete the target, which may hold
  // files we did not put there.
  for (const targetDir of targetDirs) {
    copyRecursive(SOURCE_DIR, targetDir);
    console.log(`Installed signal-scout to ${targetDir}`);
  }
  console.log("Invoke it in Claude Code or OpenCode with:");
  console.log("  /signal-scout https://your-startup.com");
}

main();
