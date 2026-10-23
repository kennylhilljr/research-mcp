// @ts-nocheck: plain JavaScript, kept out of the host project's type check
// Shared helpers for the SDD tools. Zero dependencies; Node 20 or later.
// Every tool in tools/ imports from this file so the rules live in one place.
import { readFileSync, readdirSync, statSync, existsSync, realpathSync } from "node:fs";
import { join, relative, dirname, resolve, sep } from "node:path";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";

export const FRAMEWORK_VERSION = "1.1.1";

// ---------------------------------------------------------------------------
// Requirement IDs
// ---------------------------------------------------------------------------
// Acceptance criteria:      TECH-2           (what tests and code cite with @spec)
// Typed component IDs:      TECH-US-1, TECH-FR-1, TECH-NFR-1, TECH-INV-1, TECH-OUT-1
// Parent PRD IDs:           FR-3, NFR-1, OUT-1, INV-1
export const RESERVED_PREFIXES = new Set(["FR", "NFR", "OUT", "INV", "US", "AC", "ADR", "SPEC", "LLD", "PRD", "M", "S", "P"]);
export const CRITERION_RE = /^([A-Z][A-Z0-9]{1,9})-(\d+)$/;
export const TYPED_RE = /^([A-Z][A-Z0-9]{1,9})-(US|FR|NFR|INV|OUT)-(\d+)$/;
export const PARENT_RE = /^(FR|NFR|OUT|INV)-(\d+)$/;
export const SPEC_ANNOTATION_RE = /@spec\s+([A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*(?:\s*,\s*[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*)*)/g;

// A project may allow a richer criterion form (for example AM-PRIV-001-AC1) with
// ids.criterionPattern in sdd.config.json: a regular expression whose named group "prefix"
// gives the component prefix. The default <PREFIX>-<n> form is always accepted.
let extraCriterionRe = null;
export function setCriterionPattern(pattern) {
  extraCriterionRe = null;
  if (!pattern) return;
  try {
    extraCriterionRe = new RegExp(pattern);
  } catch (e) {
    throw new Error(`ids.criterionPattern in sdd.config.json is not a valid regular expression: ${e.message}`);
  }
}

export function classifyId(raw) {
  const id = cleanCell(raw);
  if (extraCriterionRe) {
    const x = extraCriterionRe.exec(id);
    if (x && x[0] === id) {
      const prefix = x.groups?.prefix || id.split("-")[0];
      if (!RESERVED_PREFIXES.has(prefix)) return { id, kind: "criterion", prefix };
    }
  }
  let m = TYPED_RE.exec(id);
  if (m && !RESERVED_PREFIXES.has(m[1])) return { id, kind: m[2].toLowerCase(), prefix: m[1] };
  m = PARENT_RE.exec(id);
  if (m) return { id, kind: "parent-" + m[1].toLowerCase(), prefix: null };
  m = CRITERION_RE.exec(id);
  if (m && !RESERVED_PREFIXES.has(m[1])) return { id, kind: "criterion", prefix: m[1] };
  return null;
}

export function cleanCell(s) {
  return String(s ?? "").replace(/\*\*|`|__/g, "").trim();
}

// ---------------------------------------------------------------------------
// Project root and configuration
// ---------------------------------------------------------------------------
export const DEFAULT_CONFIG = {
  frameworkVersion: FRAMEWORK_VERSION,
  project: { name: "", description: "", scope: null },
  paths: {
    docs: "docs",
    codeRoots: ["src"],
    testRoots: ["test", "tests"],
    testPlan: null, // null: the latest docs/test/test-plan-vN.md
    traceIndex: "docs/trace/index.yaml",
    coverage: "docs/trace/coverage.md",
    docMap: "docs/README.md",
    scopeMap: "docs/scope/scope-map.yaml",
    testResults: null, // optional JUnit XML report; gives passing and failing states
  },
  ids: { criterionPattern: null },
  approvals: { requireApprover: false },
  components: {},
  trace: { staleAfterDays: 30, reachWarnBelow: 0.8 },
  features: {
    gateHook: true,
    protectApprovedDocs: true,
    reachReport: true,
    divergenceProbe: false,
    differentialAudit: false,
  },
};

export function findRoot(start = process.cwd()) {
  let dir = resolve(start);
  for (;;) {
    if (existsSync(join(dir, "sdd.config.json"))) return dir;
    const up = dirname(dir);
    if (up === dir) return resolve(start);
    dir = up;
  }
}

export function loadConfig(root) {
  const file = join(root, "sdd.config.json");
  let user = {};
  if (existsSync(file)) user = JSON.parse(readFileSync(file, "utf8"));
  const cfg = {
    ...DEFAULT_CONFIG,
    ...user,
    project: { ...DEFAULT_CONFIG.project, ...(user.project || {}) },
    paths: { ...DEFAULT_CONFIG.paths, ...(user.paths || {}) },
    ids: { ...DEFAULT_CONFIG.ids, ...(user.ids || {}) },
    approvals: { ...DEFAULT_CONFIG.approvals, ...(user.approvals || {}) },
    components: { ...(user.components || {}) },
    trace: { ...DEFAULT_CONFIG.trace, ...(user.trace || {}) },
    features: { ...DEFAULT_CONFIG.features, ...(user.features || {}) },
  };
  setCriterionPattern(cfg.ids.criterionPattern);
  return cfg;
}

// ---------------------------------------------------------------------------
// File walking
// ---------------------------------------------------------------------------
export const IGNORED_DIRS = new Set([
  "node_modules", ".git", "dist", "build", "coverage", ".next", ".nuxt", "out", "target", "vendor",
  ".venv", "venv", "__pycache__", ".tox", ".gradle", ".idea", ".turbo", ".cache", "bin", "obj",
]);

export const DOC_IGNORED_DIRS = new Set(["node_modules", ".git"]);

export function walk(dir, { exts = null, maxFiles = 50000, ignore = IGNORED_DIRS } = {}) {
  const out = [];
  if (!existsSync(dir)) return out;
  const stack = [dir];
  while (stack.length && out.length < maxFiles) {
    const d = stack.pop();
    let entries;
    try {
      entries = readdirSync(d, { withFileTypes: true });
    } catch {
      continue;
    }
    for (const e of entries) {
      if (e.name.startsWith(".") && e.isDirectory() && e.name !== ".github" && e.name !== ".claude") continue;
      const p = join(d, e.name);
      if (e.isDirectory()) {
        if (!ignore.has(e.name)) stack.push(p);
      } else if (e.isFile()) {
        if (!exts || exts.some((x) => e.name.endsWith(x))) out.push(p);
      }
    }
  }
  return out.sort();
}

export function rel(root, p) {
  return relative(root, p).split(sep).join("/");
}

export function readText(p) {
  try {
    return readFileSync(p, "utf8").replace(/\r\n/g, "\n");
  } catch {
    return null;
  }
}

export function isBinary(text) {
  return text.slice(0, 4000).includes("\u0000");
}

// ---------------------------------------------------------------------------
// Front matter (a small YAML subset: scalars, quoted strings, inline lists)
// ---------------------------------------------------------------------------
export function parseFrontMatter(text) {
  if (!text || !text.startsWith("---")) return { data: {}, body: text || "", bodyStart: 0, hasFrontMatter: false };
  const end = text.indexOf("\n---", 3);
  if (end === -1) return { data: {}, body: text, bodyStart: 0, hasFrontMatter: false };
  const raw = text.slice(3, end).replace(/^\r?\n/, "");
  const data = parseYaml(raw);
  const after = text.indexOf("\n", end + 4);
  const body = after === -1 ? "" : text.slice(after + 1);
  const bodyStart = text.slice(0, after + 1).split("\n").length - 1;
  return { data, body, bodyStart, hasFrontMatter: true };
}

function parseScalar(v) {
  v = v.trim();
  if (v === "") return "";
  if ((v.startsWith('"') && v.endsWith('"')) || (v.startsWith("'") && v.endsWith("'"))) return v.slice(1, -1);
  if (v.startsWith("[") && v.endsWith("]")) {
    const inner = v.slice(1, -1).trim();
    if (!inner) return [];
    return inner.split(",").map((x) => parseScalar(x));
  }
  if (v === "true") return true;
  if (v === "false") return false;
  if (v === "null" || v === "~") return null;
  if (/^-?\d+(\.\d+)?$/.test(v)) return Number(v);
  return v;
}

function stripComment(line) {
  let q = null;
  for (let i = 0; i < line.length; i++) {
    const c = line[i];
    if (q) {
      if (c === q) q = null;
    } else if ((c === '"' || c === "'") && (i === 0 || /[\s:[,]/.test(line[i - 1]))) q = c;
    else if (c === "#" && (i === 0 || /\s/.test(line[i - 1]))) return line.slice(0, i).replace(/\s+$/, "");
  }
  return line;
}

// Indentation-based mappings, "- item" scalar lists, inline lists, comments.
export function parseYaml(raw) {
  const lines = raw.split(/\r?\n/);
  const root = {};
  const stack = [{ indent: -1, obj: root, key: null }];
  for (let i = 0; i < lines.length; i++) {
    const line = stripComment(lines[i]);
    if (!line.trim() || line.trim().startsWith("#")) continue;
    const indent = line.length - line.trimStart().length;
    const t = line.trim();
    while (stack.length > 1 && indent <= stack[stack.length - 1].indent) stack.pop();
    const parent = stack[stack.length - 1];
    if (t.startsWith("- ")) {
      const container = parent.obj;
      if (Array.isArray(container)) container.push(parseScalar(t.slice(2)));
      continue;
    }
    const m = /^([^:]+):(.*)$/.exec(t);
    if (!m) continue;
    const key = m[1].trim().replace(/^["']|["']$/g, "");
    const val = m[2];
    if (val.trim() === "") {
      // nested mapping or list: peek next meaningful line
      let j = i + 1;
      while (j < lines.length && (!lines[j].trim() || lines[j].trim().startsWith("#"))) j++;
      const next = lines[j] || "";
      const child = next.trim().startsWith("- ") ? [] : {};
      parent.obj[key] = child;
      stack.push({ indent, obj: child, key });
    } else {
      parent.obj[key] = parseScalar(val);
    }
  }
  return root;
}

function yamlScalar(v) {
  if (v === null || v === undefined) return "null";
  if (Array.isArray(v)) return "[" + v.map(yamlScalar).join(", ") + "]";
  if (typeof v === "number" || typeof v === "boolean") return String(v);
  const s = String(v);
  if (s === "" || /[:#\[\]{},"']|^\s|\s$|^(true|false|null|~|-?\d+(\.\d+)?)$/.test(s)) return JSON.stringify(s);
  return s;
}

export function toYaml(obj, indent = 0) {
  const pad = " ".repeat(indent);
  let out = "";
  for (const [k, v] of Object.entries(obj)) {
    if (v && typeof v === "object" && !Array.isArray(v)) {
      out += `${pad}${k}:\n` + toYaml(v, indent + 2);
    } else {
      out += `${pad}${k}: ${yamlScalar(v)}\n`;
    }
  }
  return out;
}

// ---------------------------------------------------------------------------
// Markdown tables
// ---------------------------------------------------------------------------
export function splitRow(line) {
  let s = line.trim();
  if (s.startsWith("|")) s = s.slice(1);
  if (s.endsWith("|")) s = s.slice(0, -1);
  const cells = [];
  let cur = "";
  let inCode = false;
  for (let i = 0; i < s.length; i++) {
    const c = s[i];
    if (c === "`") inCode = !inCode;
    if (c === "\\" && s[i + 1] === "|") {
      cur += "|";
      i++;
      continue;
    }
    if (c === "|" && !inCode) {
      cells.push(cur.trim());
      cur = "";
    } else cur += c;
  }
  cells.push(cur.trim());
  return cells;
}

export function parseTables(body, lineOffset = 0) {
  const lines = body.split(/\r?\n/);
  const tables = [];
  let inFence = false;
  for (let i = 0; i < lines.length - 1; i++) {
    if (/^\s*```/.test(lines[i])) inFence = !inFence;
    if (inFence) continue;
    if (/^\s*\|/.test(lines[i]) && /^\s*\|?\s*:?-{3,}/.test(lines[i + 1])) {
      const headers = splitRow(lines[i]).map((h) => cleanCell(h).toLowerCase());
      const rows = [];
      let j = i + 2;
      while (j < lines.length && /^\s*\|/.test(lines[j])) {
        const cells = splitRow(lines[j]);
        const row = { _line: lineOffset + j + 1, _cells: cells };
        headers.forEach((h, k) => (row[h] = cells[k] ?? ""));
        rows.push(row);
        j++;
      }
      tables.push({ headers, rows, line: lineOffset + i + 1 });
      i = j - 1;
    }
  }
  return tables;
}

// ---------------------------------------------------------------------------
// Documents
// ---------------------------------------------------------------------------
export const VERSIONED_RE = /^(.*)-v(\d+)\.md$/;
export const DOC_STATUSES = new Set(["draft", "in-review", "approved", "superseded"]);
export const ADR_STATUSES = new Set(["proposed", "accepted", "rejected", "superseded", "deprecated"]);
export const FROZEN_STATUSES = new Set(["approved", "superseded", "accepted", "rejected", "deprecated"]);

export function loadDocs(root, cfg) {
  const docsDir = join(root, cfg.paths.docs);
  // docs/ folders such as build/ hold documents, so only skip version control and dependencies here
  const files = walk(docsDir, { exts: [".md"], ignore: DOC_IGNORED_DIRS });
  const docs = [];
  for (const f of files) {
    const r = rel(root, f);
    if (r.includes("/templates/")) continue;
    const text = readText(f) ?? "";
    const fm = parseFrontMatter(text);
    const name = f.split(sep).pop();
    const vm = VERSIONED_RE.exec(name);
    docs.push({
      path: f,
      rel: r,
      name,
      family: vm ? rel(root, join(dirname(f), vm[1])) : null,
      fileVersion: vm ? Number(vm[2]) : null,
      isAdr: r.startsWith(`${cfg.paths.docs}/adr/`) && /^\d{4}-/.test(name),
      data: fm.data,
      body: fm.body,
      bodyStart: fm.bodyStart,
      hasFrontMatter: fm.hasFrontMatter,
      text,
    });
  }
  // mark latest version per family
  const latest = new Map();
  for (const d of docs) {
    if (!d.family) continue;
    const cur = latest.get(d.family);
    if (!cur || d.fileVersion > cur.fileVersion) latest.set(d.family, d);
  }
  for (const d of docs) d.isLatest = !d.family || latest.get(d.family) === d;
  return docs;
}

export function docStatus(d) {
  return String(d.data.status || "").toLowerCase();
}

// Collect requirement definitions from the PRDs.
// For each document family the latest approved version is the one enforced; a newer draft
// (for example v2 while v1 is approved) adds the IDs it introduces, without enforcement.
export function collectDefinitions(docs) {
  const defs = new Map();
  const duplicates = [];
  const families = new Map();
  for (const d of docs) {
    const type = String(d.data.type || "");
    if (!(type === "prd" || type === "prd-component")) continue;
    const key = d.family || d.rel;
    if (!families.has(key)) families.set(key, []);
    families.get(key).push(d);
  }
  const selected = [];
  for (const list of families.values()) {
    list.sort((a, b) => (b.fileVersion || 0) - (a.fileVersion || 0));
    const approved = list.find((d) => docStatus(d) === "approved");
    if (approved) selected.push({ d: approved, extraOnly: false });
    if (list[0] !== approved) selected.push({ d: list[0], extraOnly: !!approved });
  }
  const own = new Map();
  for (const { d, extraOnly } of selected) {
    const type = String(d.data.type || "");
    for (const t of parseTables(d.body, d.bodyStart)) {
      if (t.headers[0] !== "id" || isHistoryTable(t)) continue;
      for (const row of t.rows) {
        const c = classifyId(row._cells[0]);
        if (!c) continue;
        const key = d.family || d.rel;
        if (extraOnly && own.get(c.id) === key) continue; // already defined by the approved version
        const entry = {
          ...c,
          file: d.rel,
          line: row._line,
          docType: type,
          docStatus: docStatus(d),
          docPrefix: d.data.prefix || null,
          priority: cleanCell(row.priority || ""),
          text: cleanCell(row.criterion || row.requirement || row.story || row.metric || row["the system must never"] || row._cells[1] || ""),
          headers: t.headers,
          notation: String(d.data.notation || "ears").toLowerCase(),
        };
        if (defs.has(c.id)) duplicates.push({ id: c.id, first: defs.get(c.id), second: entry });
        else {
          defs.set(c.id, entry);
          own.set(c.id, key);
        }
      }
    }
  }
  return { defs, duplicates };
}

// The "ID history" table of a PRD records withdrawn, superseded, split and merged IDs.
// Its rows are not definitions.
export const ID_HISTORY_STATUSES = new Set(["withdrawn", "superseded", "split", "merged"]);
export function isHistoryTable(t) {
  return t.headers[0] === "id" && t.headers.includes("replaced by");
}

// Every ID each version of a PRD defines, and its ID history rows: used to check the ID lifecycle.
export function idVersions(docs) {
  const out = [];
  for (const d of docs) {
    const type = String(d.data.type || "");
    if (!(type === "prd" || type === "prd-component")) continue;
    const ids = new Map();
    const history = new Map();
    for (const t of parseTables(d.body, d.bodyStart)) {
      if (t.headers[0] !== "id") continue;
      for (const row of t.rows) {
        const c = classifyId(row._cells[0]);
        if (!c) continue;
        if (isHistoryTable(t)) history.set(c.id, { status: cleanCell(row.status).toLowerCase(), replacedBy: cleanCell(row["replaced by"]), line: row._line });
        else ids.set(c.id, { text: cleanCell(row.criterion || row.requirement || row.story || row._cells[1] || ""), line: row._line });
      }
    }
    out.push({ d, family: d.family || d.rel, version: d.fileVersion || 0, ids, history });
  }
  return out;
}

// The test plan: the configured path, or the latest docs/test/test-plan-vN.md (approved first).
export function findTestPlan(root, cfg, docs = loadDocs(root, cfg)) {
  if (cfg.paths.testPlan) return cfg.paths.testPlan;
  const plans = docs.filter((d) => String(d.data.type || "") === "test-plan" && d.family).sort((a, b) => b.fileVersion - a.fileVersion);
  const pick = plans.find((d) => docStatus(d) === "approved") || plans[0];
  return pick ? pick.rel : `${cfg.paths.docs}/test/test-plan-v1.md`;
}

// ---------------------------------------------------------------------------
// Components, plans and the artifacts that govern them
// ---------------------------------------------------------------------------
// The component a criterion belongs to: the configured component with that prefix,
// or the lowercased prefix when the component is not configured.
export function componentOfPrefix(cfg, prefix) {
  for (const [name, c] of Object.entries(cfg.components)) if (c.prefix && c.prefix === prefix) return name;
  return prefix ? String(prefix).toLowerCase() : null;
}

export function prefixOfComponent(cfg, name) {
  return cfg.components[name]?.prefix || String(name).toUpperCase();
}

// Resolve a word typed by a person or passed as a skill argument to a component name.
export function resolveComponent(cfg, word) {
  const w = String(word || "").trim();
  if (!w) return null;
  for (const [name, c] of Object.entries(cfg.components)) {
    if (name.toLowerCase() === w.toLowerCase() || (c.prefix && c.prefix.toLowerCase() === w.toLowerCase())) return name;
  }
  return null;
}

// Does this document belong to the component? By its prefix in front matter, or by its file name (LLD-tech-v1.md).
export function docIsForComponent(d, cfg, name) {
  const prefix = prefixOfComponent(cfg, name);
  if (d.data.prefix) return String(d.data.prefix) === prefix;
  if (d.data.component) return String(d.data.component).toLowerCase() === name.toLowerCase();
  return new RegExp(`-${name}-v\\d+\\.md$`, "i").test(d.name);
}

// The components a milestone plan covers: front matter "components" or "component",
// otherwise the components whose criteria the plan cites.
export function planComponents(d, cfg) {
  const fm = d.data.components ?? d.data.component;
  if (fm && !(Array.isArray(fm) && !fm.length)) return (Array.isArray(fm) ? fm : [fm]).map((x) => resolveComponent(cfg, x) || String(x).toLowerCase());
  // Any token that classifies as an acceptance criterion counts, so a configured richer
  // ID form (ids.criterionPattern) is recognized as well as <PREFIX>-<n>.
  const out = new Set();
  const known = new Set(Object.values(cfg.components).map((c) => c.prefix).filter(Boolean));
  for (const [token] of d.body.matchAll(/[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+/g)) {
    const c = classifyId(token);
    if (!c || c.kind !== "criterion" || /^M\d+$/.test(c.prefix)) continue;
    if (known.size && !known.has(c.prefix)) continue;
    out.add(componentOfPrefix(cfg, c.prefix));
  }
  return [...out];
}

// The organizational scope map: L0 to L3. These levels describe organizational scope only;
// they are not document stages and not gates.
export const SCOPE_LEVELS = ["L0", "L1", "L2", "L3"];

export function loadScopeMap(root, cfg) {
  const p = join(root, cfg.paths.scopeMap || "");
  if (!cfg.paths.scopeMap || !existsSync(p)) return { scopes: {}, path: null };
  const data = parseYaml(readFileSync(p, "utf8").replace(/\r\n/g, "\n"));
  return { scopes: data.scopes || {}, path: cfg.paths.scopeMap };
}

// ---------------------------------------------------------------------------
// @spec annotations
// ---------------------------------------------------------------------------
const TEST_FILE_RE = /(^|\/)(test|tests|__tests__|spec)\/|\.(test|spec)\.[a-z0-9]+$|_test\.[a-z0-9]+$|(^|\/)test_[^/]+$/i;

export function isTestPath(r, cfg) {
  if (cfg.paths.testRoots.some((t) => r === t || r.startsWith(t + "/"))) return true;
  return TEST_FILE_RE.test(r);
}

export function scanAnnotations(root, cfg) {
  const roots = [...new Set([...cfg.paths.codeRoots, ...cfg.paths.testRoots])];
  const seen = new Set();
  const out = [];
  for (const r0 of roots) {
    for (const f of walk(join(root, r0))) {
      if (seen.has(f)) continue;
      seen.add(f);
      const text = readText(f);
      if (!text || isBinary(text) || text.length > 2_000_000) continue;
      const r = rel(root, f);
      const lines = text.split(/\r?\n/);
      lines.forEach((line, i) => {
        SPEC_ANNOTATION_RE.lastIndex = 0;
        let m;
        while ((m = SPEC_ANNOTATION_RE.exec(line))) {
          const ids = m[1].split(",").map((x) => x.trim()).filter(Boolean);
          out.push({ file: r, line: i + 1, ids, isTest: isTestPath(r, cfg) });
        }
      });
    }
  }
  return out;
}

export function listSourceFiles(root, cfg) {
  const files = [];
  for (const r0 of cfg.paths.codeRoots) {
    for (const f of walk(join(root, r0))) {
      const r = rel(root, f);
      if (!isTestPath(r, cfg) && !r.split("/").pop().startsWith(".")) files.push(r);
    }
  }
  return files;
}

// ---------------------------------------------------------------------------
// Git (optional; every caller must cope with null)
// ---------------------------------------------------------------------------
export function git(root, args) {
  try {
    return execFileSync("git", args, { cwd: root, encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] }).trim();
  } catch {
    return null;
  }
}

export function isGitRepo(root) {
  return git(root, ["rev-parse", "--is-inside-work-tree"]) === "true";
}

// ---------------------------------------------------------------------------
// Output helpers
// ---------------------------------------------------------------------------
// Flags that never take a value, so "init --git ../app" keeps ../app as the folder.
export const BOOLEAN_FLAGS = new Set(["apply", "git", "json", "force", "dry-run", "allow-dirty", "check", "advisory", "write", "help", "overwrite"]);

export function parseArgs(argv) {
  const args = { _: [] };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "-h") args.help = true;
    else if (a.startsWith("--")) {
      const [k, v] = a.slice(2).split("=");
      if (v !== undefined) args[k] = v;
      else if (BOOLEAN_FLAGS.has(k)) args[k] = true;
      else if (argv[i + 1] && !argv[i + 1].startsWith("--")) args[k] = argv[++i];
      else args[k] = true;
    } else args._.push(a);
  }
  return args;
}

// True when this module is the script node was started with (robust to symlinks and Windows drive case).
export function isMain(metaUrl) {
  if (!process.argv[1]) return false;
  const norm = (p) => {
    let r;
    try {
      r = realpathSync(p);
    } catch {
      r = resolve(p);
    }
    return process.platform === "win32" ? r.toLowerCase() : r;
  };
  return norm(fileURLToPath(metaUrl)) === norm(process.argv[1]);
}

export function report(name, { errors, warnings, infos = [] }, { json = false, advisory = false } = {}) {
  if (json) {
    console.log(JSON.stringify({ tool: name, errors, warnings, infos }, null, 2));
  } else {
    for (const e of errors) console.log(`ERROR  ${e.file ? e.file + (e.line ? ":" + e.line : "") + "  " : ""}${e.msg}`);
    for (const w of warnings) console.log(`WARN   ${w.file ? w.file + (w.line ? ":" + w.line : "") + "  " : ""}${w.msg}`);
    for (const n of infos) console.log(`INFO   ${n.msg}`);
    console.log(`${name}: ${errors.length} error(s), ${warnings.length} warning(s)${advisory && errors.length ? " (advisory mode: not failing)" : ""}`);
  }
  return errors.length && !advisory ? 1 : 0;
}
