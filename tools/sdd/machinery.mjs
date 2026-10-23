// @ts-nocheck: plain JavaScript, kept out of the host project's type check
// What the framework installs into a repository, and safe file writing.
// Used by `sdd init` (new repositories) and `sdd adopt` (existing repositories).
import { existsSync, mkdirSync, readFileSync, writeFileSync, copyFileSync, statSync } from "node:fs";
import { join, dirname, resolve, extname, basename } from "node:path";
import { fileURLToPath } from "node:url";
import { walk, rel } from "../lib/sdd-lib.mjs";

// Root of the framework repository this script lives in.
export const FRAMEWORK_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..", "..");
export const SCAFFOLD_DIR = join(FRAMEWORK_ROOT, "tools", "sdd", "scaffold");

// Directories copied as-is from the framework into a target repository.
export const MACHINERY_DIRS = [
  ".claude/skills",
  ".claude/agents",
  ".claude/commands",
  "tools/lib",
  "tools/spec-lint",
  "tools/trace-check",
  "tools/hooks",
  "tools/sdd",
  "docs/templates",
  "docs/standards",
  "docs/guide",
];
export const MACHINERY_FILES = [
  "docs/assets/diagrams/sdd-doc-layers.svg",
  "docs/assets/diagrams/sdd-skill-chain.svg",
  ".devcontainer/devcontainer.json",
];
// Files that come from tools/sdd/scaffold (target path -> scaffold source)
export const SCAFFOLD_FILES = {
  "AGENTS.md": "AGENTS.md",
  "CLAUDE.md": "CLAUDE.md",
  ".claude/settings.json": "settings.json",
  "docs/README.md": "docs-README.md",
  "docs/glossary.md": "glossary.md",
  "docs/trace/index.yaml": "trace-index.yaml",
  "docs/trace/coverage.md": "coverage.md",
  "docs/test/test-plan-v1.md": "test-plan-v1.md",
  "docs/scope/scope-map.yaml": "scope-map.yaml",
  "docs/adr/README.md": "adr-README.md",
};
export const EMPTY_DIRS = [
  "docs/vision", "docs/research", "docs/prd/components", "docs/adr", "docs/spec", "docs/lld", "docs/contracts",
  "docs/build", "docs/runbooks", "docs/postmortems", "docs/trace/audits",
];

export function machineryFiles() {
  const files = [];
  for (const d of MACHINERY_DIRS) {
    for (const f of walk(join(FRAMEWORK_ROOT, d))) files.push(rel(FRAMEWORK_ROOT, f));
  }
  for (const f of MACHINERY_FILES) if (existsSync(join(FRAMEWORK_ROOT, f))) files.push(f);
  return files;
}

export function fill(text, vars) {
  return text.replace(/\{\{([A-Z_]+)\}\}/g, (m, k) => (vars[k] !== undefined ? String(vars[k]) : m));
}

// A plan is a list of actions; nothing touches the disk until apply() runs.
// kind: "create" (new file), "propose" (target exists: the new version goes to .sdd-proposed/<path>, outside
// .claude/ and the source tree, so nothing loads it twice), "update" (overwrite; only sdd upgrade --overwrite), "skip", "mkdir"
export const PROPOSED_DIR = ".sdd-proposed";
export class Plan {
  constructor(target) {
    this.target = resolve(target);
    this.actions = [];
  }
  file(path, content, { onConflict = "propose" } = {}) {
    const abs = join(this.target, path);
    if (existsSync(abs)) {
      const cur = readFileSync(abs);
      const same = Buffer.isBuffer(content) ? cur.equals(content) : cur.toString("utf8") === content;
      if (same) return this.actions.push({ kind: "skip", path, reason: "identical" });
      if (onConflict === "keep") return this.actions.push({ kind: "skip", path, reason: "exists; kept as is" });
      if (onConflict === "overwrite") return this.actions.push({ kind: "update", path, content });
      const proposed = `${PROPOSED_DIR}/${path}`;
      if (existsSync(join(this.target, proposed))) {
        const cur2 = readFileSync(join(this.target, proposed));
        const same2 = Buffer.isBuffer(content) ? cur2.equals(content) : cur2.toString("utf8") === content;
        if (same2) return this.actions.push({ kind: "skip", path: proposed, reason: "proposal already exists" });
      }
      return this.actions.push({ kind: "propose", path: proposed, of: path, content });
    }
    this.actions.push({ kind: "create", path, content });
  }
  copy(fromAbs, path, opts) {
    this.file(path, readFileSync(fromAbs), opts);
  }
  dir(path) {
    const abs = join(this.target, path);
    if (!existsSync(abs)) this.actions.push({ kind: "mkdir", path });
  }
  summary() {
    const by = (k) => this.actions.filter((a) => a.kind === k);
    return { create: by("create"), propose: by("propose"), update: by("update"), skip: by("skip"), mkdir: by("mkdir") };
  }
  apply() {
    const done = [];
    for (const a of this.actions) {
      const abs = join(this.target, a.path);
      if (a.kind === "mkdir") {
        mkdirSync(abs, { recursive: true });
        const keep = join(abs, ".gitkeep");
        if (!existsSync(keep)) writeFileSync(keep, "");
        done.push(a);
      } else if (a.kind === "create") {
        if (existsSync(abs)) continue; // never overwrite, even if the plan is stale
        mkdirSync(dirname(abs), { recursive: true });
        writeFileSync(abs, a.content);
        done.push(a);
      } else if (a.kind === "propose" || a.kind === "update") {
        // proposals live in .sdd-proposed/; updates only come from sdd upgrade --overwrite
        mkdirSync(dirname(abs), { recursive: true });
        writeFileSync(abs, a.content);
        done.push(a);
      }
    }
    return done;
  }
  print(log = console.log) {
    const s = this.summary();
    for (const a of s.mkdir) log(`  mkdir    ${a.path}/`);
    for (const a of s.create) log(`  create   ${a.path}`);
    for (const a of s.propose) log(`  propose  ${a.path}   (${a.of} already exists and is left untouched)`);
    for (const a of s.update) log(`  update   ${a.path}`);
    const skipped = s.skip.length;
    log(`  ${s.create.length} to create, ${s.propose.length} proposals${s.update.length ? `, ${s.update.length} updates` : ""}, ${s.mkdir.length} folders, ${skipped} unchanged`);
  }
}

export function addMachinery(plan, { onConflict = "propose" } = {}) {
  for (const r of machineryFiles()) {
    if (resolve(plan.target) === FRAMEWORK_ROOT) continue;
    plan.copy(join(FRAMEWORK_ROOT, r), r, { onConflict });
  }
}

export function scaffoldText(name, vars) {
  return fill(readFileSync(join(SCAFFOLD_DIR, name), "utf8"), vars);
}

export function today() {
  return new Date().toISOString().slice(0, 10);
}

export function isDirEmpty(dir) {
  if (!existsSync(dir)) return true;
  const entries = walk(dir);
  return entries.filter((f) => !basename(f).startsWith(".")).length === 0;
}

export { statSync, copyFileSync };
