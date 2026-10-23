#!/usr/bin/env node
// @ts-nocheck: plain JavaScript, kept out of the host project's type check
// Protect-approved hook (Claude Code PreToolUse, matcher "Edit|Write|MultiEdit").
// Approved document versions are frozen: a change goes into the next numbered version.
// Exit 2 blocks the edit and explains why; every other path exits 0.
import { readFileSync, existsSync } from "node:fs";
import { resolve, relative, sep } from "node:path";
import { fileURLToPath } from "node:url";
import { findRoot, loadConfig, parseFrontMatter, FROZEN_STATUSES, isMain } from "../lib/sdd-lib.mjs";

export function decide(root, filePath) {
  const cfg = loadConfig(root);
  if (!cfg.features.protectApprovedDocs || !filePath) return { allow: true };
  const abs = resolve(root, filePath);
  const r = relative(root, abs).split(sep).join("/");
  if (!r.startsWith(cfg.paths.docs + "/") || !r.endsWith(".md")) return { allow: true };
  if (r.startsWith(`${cfg.paths.docs}/trace/`) || r.startsWith(`${cfg.paths.docs}/templates/`)) return { allow: true };
  if (!existsSync(abs)) return { allow: true };
  const { data } = parseFrontMatter(readFileSync(abs, "utf8"));
  const status = String(data.status || "").toLowerCase();
  if (!FROZEN_STATUSES.has(status)) return { allow: true };
  const isAdr = r.startsWith(`${cfg.paths.docs}/adr/`);
  return {
    allow: false,
    reason: isAdr
      ? `${r} is ${status} and frozen. Record a change as a new ADR that supersedes it: node tools/sdd/cli.mjs new adr --name <slug>`
      : `${r} is ${status} and frozen. Create the next version instead: node tools/sdd/cli.mjs new --next ${r}`,
  };
}

function main() {
  let input = {};
  try {
    input = JSON.parse(readFileSync(0, "utf8") || "{}");
  } catch {
    process.exit(0);
  }
  if (!["Edit", "Write", "MultiEdit"].includes(input.tool_name)) process.exit(0);
  const root = findRoot(process.env.CLAUDE_PROJECT_DIR || input.cwd || process.cwd());
  const result = decide(root, input.tool_input?.file_path);
  if (result.allow) process.exit(0);
  process.stderr.write(result.reason + "\n");
  process.exit(2);
}

if (isMain(import.meta.url)) {
  try {
    main();
  } catch {
    process.exit(0);
  }
}
