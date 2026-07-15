#!/usr/bin/env node
"use strict";

const fs = require("fs");
const path = require("path");
const os = require("os");

const SKILL_NAME = "signal-scout";
const SOURCE_DIR = path.join(__dirname, "..", "skills", SKILL_NAME);

function parseTargetDir(argv) {
  const flagIndex = argv.indexOf("--dir");
  if (flagIndex !== -1 && argv[flagIndex + 1]) {
    return argv[flagIndex + 1];
  }
  return path.join(os.homedir(), ".agents", "skills", SKILL_NAME);
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
  const targetDir = parseTargetDir(process.argv.slice(2));

  if (!fs.existsSync(SOURCE_DIR)) {
    console.error(`Skill source not found at ${SOURCE_DIR}`);
    process.exit(1);
  }

  fs.rmSync(targetDir, { recursive: true, force: true });
  copyRecursive(SOURCE_DIR, targetDir);

  console.log(`Installed signal-scout to ${targetDir}`);
  console.log("Invoke it in Claude Code or OpenCode with:");
  console.log("  /signal-scout https://your-startup.com");
}

main();
