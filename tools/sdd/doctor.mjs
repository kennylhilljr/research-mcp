// @ts-nocheck: plain JavaScript, kept out of the host project's type check
// sdd doctor: check that a local environment can run the framework.
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { execFileSync } from "node:child_process";
import { findRoot, loadConfig, isGitRepo } from "../lib/sdd-lib.mjs";
import { lint } from "../spec-lint/spec-lint.mjs";
import { analyze } from "../trace-check/trace-check.mjs";

function version(cmd, args = ["--version"]) {
  try {
    return execFileSync(cmd, args, { encoding: "utf8", stdio: ["ignore", "pipe", "ignore"], timeout: 8000, shell: process.platform === "win32" })
      .trim()
      .split("\n")[0];
  } catch {
    return null;
  }
}

export function runDoctor(target, opts = {}, log = console.log) {
  const root = findRoot(target || process.cwd());
  const checks = [];
  const add = (name, ok, detail, required = true) => checks.push({ name, ok, detail, required });

  const major = Number(process.versions.node.split(".")[0]);
  add("Node.js 20 or later", major >= 20, `found ${process.versions.node}`);
  const gitV = version("git");
  add("git", !!gitV, gitV || "not found (needed for staleness and reach checks)", false);
  add("inside a git repository", isGitRepo(root), isGitRepo(root) ? root : "run git init to enable staleness and reach checks", false);
  const claude = version("claude");
  add("Claude Code CLI (claude)", !!claude, claude || "not found; install from https://code.claude.com, or use the desktop or web app", false);
  const codex = version("codex");
  add("Codex CLI (optional)", !!codex, codex || "not installed; AGENTS.md lets Codex follow the framework by hand", false);

  add("sdd.config.json", existsSync(join(root, "sdd.config.json")), existsSync(join(root, "sdd.config.json")) ? "found" : "missing; run sdd init or sdd adopt");
  for (const f of ["AGENTS.md", "CLAUDE.md"]) add(f, existsSync(join(root, f)), existsSync(join(root, f)) ? "found" : "missing");
  const settingsPath = join(root, ".claude", "settings.json");
  let hooksOk = false;
  if (existsSync(settingsPath)) {
    try {
      const s = JSON.parse(readFileSync(settingsPath, "utf8"));
      const text = JSON.stringify(s.hooks || {});
      hooksOk = text.includes("gate.mjs") && text.includes("protect-approved.mjs");
    } catch {
      hooksOk = false;
    }
  }
  add(".claude/settings.json registers the gate hooks", hooksOk, hooksOk ? "gate and protect-approved hooks registered" : "hooks not registered (see .claude/settings.sdd-proposed.json if adopt created one)");
  const skills = ["sdd-intake", "sdd-spec", "sdd-clarify", "sdd-hld", "sdd-lld", "sdd-tasks", "sdd-implement", "sdd-verify", "sdd-adopt", "sdd-triage"];
  const missingSkills = skills.filter((s) => !existsSync(join(root, ".claude", "skills", s, "SKILL.md")));
  add("skills installed", missingSkills.length === 0, missingSkills.length ? `missing: ${missingSkills.join(", ")}` : `${skills.length} skills`);
  const agents = ["analyst", "product-writer", "architect", "security-reviewer", "component-designer", "test-architect", "sre", "planner", "implementer", "verifier", "doc-steward"];
  const missingAgents = agents.filter((a) => !existsSync(join(root, ".claude", "agents", `${a}.md`)));
  add("agent personas installed", missingAgents.length === 0, missingAgents.length ? `missing: ${missingAgents.join(", ")}` : `${agents.length} personas`);

  let lintRes = null;
  let traceRes = null;
  try {
    const cfg = loadConfig(root);
    lintRes = lint(root, cfg);
    traceRes = analyze(root, cfg);
    add("spec-lint", lintRes.errors.length === 0, `${lintRes.errors.length} error(s), ${lintRes.warnings.length} warning(s)`, false);
    add("trace-check", traceRes.errors.length === 0, `${traceRes.errors.length} error(s), ${traceRes.warnings.length} warning(s)`, false);
  } catch (e) {
    add("spec-lint and trace-check run", false, e.message);
  }

  log(`sdd doctor -> ${root}`);
  for (const c of checks) log(`  ${c.ok ? "ok  " : c.required ? "FAIL" : "warn"}  ${c.name}: ${c.detail}`);
  const failed = checks.filter((c) => !c.ok && c.required);
  log(failed.length ? `\n${failed.length} required check(s) failed.` : "\nThe environment is ready.");
  return failed.length ? 1 : 0;
}
