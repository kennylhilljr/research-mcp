// @ts-nocheck: plain JavaScript, kept out of the host project's type check
// sdd new, sdd docmap and sdd catalog: create documents from templates, keep the doc map
// and the skill and agent catalog current.
import { existsSync, readFileSync, writeFileSync, mkdirSync, readdirSync } from "node:fs";
import { join, dirname, basename, resolve } from "node:path";
import { findRoot, loadConfig, loadDocs, parseFrontMatter, readText, walk, rel, VERSIONED_RE, docStatus, docIsForComponent, loadScopeMap, SCOPE_LEVELS } from "../lib/sdd-lib.mjs";
import { today } from "./machinery.mjs";

// type -> template file and destination (relative to the docs folder)
export const DOC_TYPES = {
  vision: { template: "vision-template.md", dest: () => "vision/vision" },
  research: { template: "research-template.md", dest: (o) => `research/${need(o, "name")}`, needs: ["name"] },
  prd: { template: "PRD-template.md", dest: () => "prd/PRD" },
  "prd-component": { template: "PRD-component-template.md", dest: (o) => `prd/components/PRD-${need(o, "component")}`, needs: ["component", "prefix"] },
  adr: { template: "ADR-template.md", dest: null, needs: ["name"] },
  spec: { template: "SPEC-template.md", dest: () => "spec/SPEC" },
  lld: { template: "LLD-template.md", dest: (o) => `lld/LLD-${need(o, "component")}`, needs: ["component"] },
  "test-plan": { template: "test-plan-template.md", dest: () => "test/test-plan" },
  kickoff: { template: "kickoff-template.md", dest: (o) => `build/${milestone(o)}-kickoff`, needs: ["milestone"] },
  plan: { template: "plan-template.md", dest: (o) => `build/${milestone(o)}-plan`, needs: ["milestone"] },
  handoff: { template: "handoff-template.md", dest: (o) => `build/${milestone(o)}-handoff`, needs: ["milestone"] },
  runbook: { template: "runbook-template.md", dest: (o) => `runbooks/${need(o, "name")}`, needs: ["name"] },
  postmortem: { template: "postmortem-template.md", dest: null, needs: ["name"] },
};

function milestone(o) {
  need(o, "milestone");
  return String(o.milestone).toUpperCase().replace(/[^A-Z0-9]/g, "");
}

function need(o, k) {
  if (!o[k] || o[k] === true) throw new Error(`--${k} is required for this document type`);
  return String(o[k]).toLowerCase().replace(/[^a-z0-9-]+/g, "-").replace(/^-|-$/g, "");
}

function nextVersion(dir, base) {
  if (!existsSync(dir)) return 1;
  let max = 0;
  for (const f of readdirSync(dir)) {
    const m = VERSIONED_RE.exec(f);
    if (m && m[1] === base) max = Math.max(max, Number(m[2]));
  }
  return max + 1;
}

export function newDoc(root, type, opts = {}) {
  const cfg = loadConfig(root);
  const t = DOC_TYPES[type];
  if (!t) throw new Error(`unknown type "${type}". Types: ${Object.keys(DOC_TYPES).join(", ")}`);
  for (const k of t.needs || []) need(opts, k);
  const tplPath = join(root, cfg.paths.docs, "templates", t.template);
  if (!existsSync(tplPath)) throw new Error(`template not found: ${rel(root, tplPath)}`);
  const docs = join(root, cfg.paths.docs);
  let out;
  let version = 1;
  if (type === "adr") {
    const dir = join(docs, "adr");
    const nums = existsSync(dir) ? readdirSync(dir).map((f) => Number(f.slice(0, 4))).filter((n) => !Number.isNaN(n)) : [];
    const n = String((nums.length ? Math.max(...nums) : 0) + 1).padStart(4, "0");
    out = join(dir, `${n}-${need(opts, "name")}.md`);
    opts.number = n;
  } else if (type === "postmortem") {
    out = join(docs, "postmortems", `${opts.date || today()}-${need(opts, "name")}.md`);
  } else {
    const destBase = join(docs, t.dest(opts));
    version = nextVersion(dirname(destBase), basename(destBase));
    out = `${destBase}-v${version}.md`;
  }
  if (existsSync(out)) throw new Error(`${rel(root, out)} already exists`);
  const prefix = String(opts.prefix || "").toUpperCase();
  const text = readFileSync(tplPath, "utf8")
    .replace(/\{\{TITLE\}\}/g, opts.title || opts.component || opts.name || type)
    .replace(/\{\{VERSION\}\}/g, String(version))
    .replace(/\{\{DATE\}\}/g, today())
    .replace(/\{\{COMPONENT\}\}/g, opts.component || "")
    .replace(/\{\{MILESTONE\}\}/g, opts.milestone || "")
    .replace(/\{\{NUMBER\}\}/g, opts.number || "")
    .replace(/\{\{PREFIX\}\}/g, prefix || "[PREFIX]")
    .replace(/\[PREFIX\]/g, prefix || "[PREFIX]");
  mkdirSync(dirname(out), { recursive: true });
  writeFileSync(out, text);
  return rel(root, out);
}

// Copy an approved (frozen) document into its next version as a draft.
export function nextDoc(root, path, cwd = process.cwd()) {
  // accept a path relative to the current folder or to the repository root
  const fromRoot = join(root, path);
  const abs = existsSync(fromRoot) ? fromRoot : resolve(cwd, path);
  if (!existsSync(abs)) throw new Error(`${path} does not exist`);
  path = rel(root, abs);
  const name = basename(abs);
  const m = VERSIONED_RE.exec(name);
  if (!m) throw new Error(`${path} is not a versioned document (<name>-vN.md)`);
  const next = Number(m[2]) + 1;
  const out = join(dirname(abs), `${m[1]}-v${next}.md`);
  if (existsSync(out)) throw new Error(`${rel(root, out)} already exists`);
  const text = readFileSync(abs, "utf8");
  const fm = parseFrontMatter(text);
  let head = text.slice(0, text.length - fm.body.length);
  head = head
    .replace(/^version:.*$/m, `version: ${next}`)
    .replace(/^status:.*$/m, "status: draft")
    .replace(/^approved:.*\n/m, "");
  if (/^supersedes:/m.test(head)) head = head.replace(/^supersedes:.*$/m, `supersedes: ${path}`);
  else head = head.replace(/\n---\s*\n?$/, `\nsupersedes: ${path}\n---\n`);
  const body = fm.body.replace(new RegExp(`\\(v${m[2]}\\)`, "g"), `(v${next})`);
  writeFileSync(out, head + body);
  return rel(root, out);
}

// The delivery artifact chain, in order. These are artifact types, not organizational scope
// levels: L0 to L3 are reserved for organizational scope (docs/scope/scope-map.yaml).
const CHAIN = [
  ["vision", "Vision and direction"],
  ["research", "Research"],
  ["prd", "Product specification (parent PRD)"],
  ["prd-component", "Product specification (component PRD)"],
  ["spec", "High level design (SPEC)"],
  ["lld", "Low level design (LLD)"],
  ["test-plan", "Test strategy"],
  ["kickoff", "Plan"],
  ["plan", "Plan"],
  ["handoff", "Handoff"],
  ["runbook", "Operations"],
  ["standard", "Standard"],
  ["inventory", "Adoption"],
  ["adoption-gaps", "Adoption"],
];
export const DOCMAP_START = "<!-- docmap:start -->";
export const DOCMAP_END = "<!-- docmap:end -->";

const cell = (v) => String(v ?? "").replace(/\|/g, "/");

// The organizational scope a document belongs to: its own scope_name, its component's scope,
// or the project's default scope.
function scopeOf(d, cfg) {
  if (d.data.scope_name) return String(d.data.scope_name);
  if (d.data.type === "standard") return ""; // framework standards are not tied to one scope
  for (const [name, c] of Object.entries(cfg.components)) if (c.scope && d.data.prefix && docIsForComponent(d, cfg, name)) return c.scope;
  return cfg.project.scope || "";
}

export function docmapTable(root) {
  const cfg = loadConfig(root);
  const all = loadDocs(root, cfg);
  const docs = all.filter((d) => d.family && d.isLatest);
  const order = new Map(CHAIN.map(([t], i) => [t, i]));
  docs.sort((a, b) => (order.get(a.data.type) ?? 99) - (order.get(b.data.type) ?? 99) || a.rel.localeCompare(b.rel));
  const link = (r) => r.replace(new RegExp(`^${cfg.paths.docs}/`), "");
  const lines = [DOCMAP_START, ""];

  const { scopes, path: scopePath } = loadScopeMap(root, cfg);
  lines.push("### Organizational scope map", "");
  if (Object.keys(scopes).length) {
    lines.push(`From [${link(scopePath)}](${link(scopePath)}).`, "", "| Level | Scope | Name | Parent | Owner | Status |", "| --- | --- | --- | --- | --- | --- |");
    const lvl = (k) => SCOPE_LEVELS.indexOf(String(scopes[k].level));
    for (const k of Object.keys(scopes).sort((a, b) => lvl(a) - lvl(b) || a.localeCompare(b)))
      lines.push(`| ${cell(scopes[k].level)} | \`${k}\` | ${cell(scopes[k].name)} | ${scopes[k].parent ? "`" + cell(scopes[k].parent) + "`" : ""} | ${cell(scopes[k].owner)} | ${cell(scopes[k].status)} |`);
  } else lines.push(`No scope map yet. Create ${cfg.paths.scopeMap} to record the L0 to L3 organizational scopes.`);

  lines.push("", "### Delivery artifact index", "", "| Artifact type | Latest document | Version | Status | Scope | Derives from | Owner |", "| --- | --- | --- | --- | --- | --- | --- |");
  for (const d of docs) {
    const type = (CHAIN.find(([t]) => t === d.data.type) || [null, d.data.type || "Other"])[1];
    const upstream = [].concat(d.data.derives_from || d.data.parent || []).map((u) => String(u).startsWith(cfg.paths.docs + "/") ? `[${link(String(u)).split("/").pop()}](${link(String(u))})` : cell(u)).join(", ");
    lines.push(`| ${type} | [${cell(d.data.title || d.name)}](${link(d.rel)}) | v${d.fileVersion} | ${docStatus(d) || "?"} | ${scopeOf(d, cfg) ? "`" + scopeOf(d, cfg) + "`" : ""} | ${upstream} | ${cell(d.data.owner)} |`);
  }
  for (const d of all.filter((x) => x.isAdr))
    lines.push(`| Decision (ADR) | [${cell(d.data.title || d.name)}](${link(d.rel)}) | ${d.name.slice(0, 4)} | ${docStatus(d) || "?"} | ${scopeOf(d, cfg) ? "`" + scopeOf(d, cfg) + "`" : ""} | | ${cell(d.data.owner)} |`);
  lines.push("", "Generated by `node tools/sdd/cli.mjs docmap`. Do not edit by hand.", "", DOCMAP_END);
  return lines.join("\n");
}

export function replaceBlock(text, start, end, block) {
  if (text.includes(start) && text.includes(end)) return text.slice(0, text.indexOf(start)) + block + text.slice(text.indexOf(end) + end.length);
  return text.replace(/\s*$/, "\n\n" + block + "\n");
}

export function writeDocmap(root, { check = false } = {}) {
  const cfg = loadConfig(root);
  const p = join(root, cfg.paths.docMap || `${cfg.paths.docs}/README.md`);
  const cur = readText(p) ?? "# Documentation map\n";
  const next = replaceBlock(cur, DOCMAP_START, DOCMAP_END, docmapTable(root));
  if (check) return next === cur;
  if (next !== cur) writeFileSync(p, next);
  return true;
}

// Catalog of skills, agents and commands with their versions.
export const CATALOG_START = "<!-- catalog:start -->";
export const CATALOG_END = "<!-- catalog:end -->";

export function catalogEntries(root) {
  const read = (f) => parseFrontMatter(readText(f) ?? "").data;
  const skills = [];
  const sdir = join(root, ".claude", "skills");
  if (existsSync(sdir))
    for (const d of readdirSync(sdir).sort()) {
      const f = join(sdir, d, "SKILL.md");
      if (existsSync(f)) skills.push({ file: rel(root, f), ...read(f) });
    }
  const agents = walk(join(root, ".claude", "agents"), { exts: [".md"] }).map((f) => ({ file: rel(root, f), ...read(f) }));
  const commands = walk(join(root, ".claude", "commands"), { exts: [".md"] }).map((f) => ({ file: rel(root, f), name: "/" + basename(f, ".md"), ...read(f) }));
  return { skills, agents, commands };
}

export function catalogBlock(root) {
  const { skills, agents, commands } = catalogEntries(root);
  const v = (e) => e.metadata?.version || e.version || "?";
  const short = (s) => String(s || "").replace(/\|/g, "/").split(/(?<=\.)\s/)[0];
  const L = [CATALOG_START, "", "### Skills", "", "| Skill | Version | What it does |", "| --- | --- | --- |"];
  for (const s of skills) L.push(`| [\`${s.name}\`](../../${s.file}) | ${v(s)} | ${short(s.description)} |`);
  L.push("", "### Agent personas", "", "| Persona | Version | What it does |", "| --- | --- | --- |");
  for (const a of agents) L.push(`| [\`${a.name}\`](../../${a.file}) | ${v(a)} | ${short(a.description)} |`);
  L.push("", "### Commands", "", "| Command | Version | What it does |", "| --- | --- | --- |");
  for (const c of commands) L.push(`| [\`${c.name}\`](../../${c.file}) | ${v(c)} | ${short(c.description)} |`);
  L.push("", "Generated by `node tools/sdd/cli.mjs catalog`. Do not edit by hand.", "", CATALOG_END);
  return L.join("\n");
}

export function writeCatalog(root, { check = false } = {}) {
  const p = join(root, "docs", "guide", "catalog.md");
  const cur = readText(p) ?? "# Catalog of skills, agents and commands\n";
  const next = replaceBlock(cur, CATALOG_START, CATALOG_END, catalogBlock(root));
  if (check) return next === cur;
  if (next !== cur) {
    mkdirSync(dirname(p), { recursive: true });
    writeFileSync(p, next);
  }
  return true;
}

export { findRoot };
