#!/usr/bin/env node
// @ts-nocheck: plain JavaScript, kept out of the host project's type check
// trace-check: checks the links between requirements, tests and code.
// Usage: node tools/trace-check/trace-check.mjs [--root DIR] [--write] [--base REF] [--results FILE] [--json] [--advisory]
//   --write         regenerate docs/trace/coverage.md and the evidence counts in the trace index
//   --base REF      report annotation reach for files changed since REF (for example origin/main)
//   --results FILE  a JUnit XML test report; linked criteria become passing or failing
//
// Evidence states for an acceptance criterion, in the order they are decided:
//   drifted      the verifier recorded drift for it in the trace index
//   passing      a linked test ran and passed (needs a test report)
//   failing      a linked test ran and failed (needs a test report)
//   test linked  a test cites it with @spec; no result was read
//   deferred     the owner deferred it (P2 or P3 only), in the test plan's deferred: list
//   excepted     the owner accepted an exception for it, in the test plan's excepted: list
//   planned      no test yet, but the test plan or the component's LLD maps it to planned tests
//   gap          no test and no planned evidence
// A link is structural evidence only: it does not prove the test checks what the criterion means.
import { join, dirname, resolve } from "node:path";
import { existsSync, readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import {
  findRoot, loadConfig, loadDocs, collectDefinitions, scanAnnotations, listSourceFiles, parseFrontMatter,
  parseYaml, toYaml, git, isGitRepo, parseArgs, report, readText, findTestPlan, isMain,
  componentOfPrefix, docIsForComponent, planComponents, docStatus, classifyId, parseTables } from "../lib/sdd-lib.mjs";

export const COVERAGE_START = "<!-- trace-check:coverage:start -->";
export const COVERAGE_END = "<!-- trace-check:coverage:end -->";

// Read a JUnit XML report: test case name -> passed (true) or failed (false).
// Skipped cases are left out. Works with the JUnit reporters of most test runners.
export function readJUnit(text) {
  const results = [];
  const re = /<testcase\b([^>]*?)(\/>|>([\s\S]*?)<\/testcase>)/g;
  let m;
  while ((m = re.exec(text || ""))) {
    const attrs = m[1];
    const name = /\bname="([^"]*)"/.exec(attrs)?.[1] ?? "";
    const cls = /\bclassname="([^"]*)"/.exec(attrs)?.[1] ?? "";
    const inner = m[3] || "";
    if (/<skipped\b/.test(inner)) continue;
    const unescape = (x) => x.replace(/&quot;/g, '"').replace(/&apos;/g, "'").replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&amp;/g, "&");
    results.push({ name: unescape(`${cls} ${name}`), passed: !/<(failure|error)\b/.test(inner) });
  }
  return results;
}

// Criterion IDs a text names, with "TECH-1 to TECH-4" (or "through") expanded to every ID in between.
const DONE_STATUS = /^(done|merged|complete|completed)\b/i;
// Task table cells that describe the task rather than name what it delivers.
const NOT_DELIVERED = new Set(["#", "task", "depends on", "status"]);
function criteriaIn(text) {
  const out = new Set();
  // The two ends share everything but their last number; zero padding is kept when both ends have the same width.
  for (const m of String(text).matchAll(/\b([A-Z][A-Z0-9]*-(?:[A-Z0-9]+-)*[A-Z]*)(\d+)\s+(?:to|through)\s+\1(\d+)\b/g)) {
    const width = m[2].length === m[3].length ? m[2].length : 0;
    for (let n = Number(m[2]); n <= Number(m[3]) && n - Number(m[2]) < 1000; n++) out.add(m[1] + String(n).padStart(width, "0"));
  }
  for (const [token] of String(text).matchAll(/[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+/g)) out.add(token);
  return new Set([...out].filter((id) => { const c = classifyId(id); return c && c.kind === "criterion"; }));
}

export function analyze(root, cfg = loadConfig(root), { base = null, results = null } = {}) {
  const errors = [];
  const warnings = [];
  const infos = [];
  const docs = loadDocs(root, cfg);
  const { defs } = collectDefinitions(docs);
  const annotations = scanAnnotations(root, cfg);

  // Test plan: deferred and excepted criteria (owner decisions recorded in its front matter)
  const planRel = findTestPlan(root, cfg, docs);
  const planText = readText(join(root, planRel));
  const plan = planText ? parseFrontMatter(planText) : { data: {}, body: "" };
  // Deferrals and exceptions are owner decisions: they count only once the test plan is approved.
  const list = (v) => new Set((Array.isArray(v) ? v : []).map(String));
  const planApproved = docStatus({ data: plan.data }) === "approved";
  const deferred = planApproved ? list(plan.data.deferred) : new Set();
  const excepted = planApproved ? list(plan.data.excepted) : new Set();
  for (const [k, ids] of [["deferred", list(plan.data.deferred)], ["excepted", list(plan.data.excepted)]])
    if (!planApproved && ids.size) warnings.push({ file: planRel, msg: `${k}: ${[...ids].join(", ")} is not counted until the owner approves the test plan` });
  const index = loadIndex(root, cfg);

  // Criteria due in build. Each current plan (latest version, not superseded) is read on its own and the results
  // are combined. A plan that names no criteria of a component it covers makes all of them due. Otherwise, when
  // its task table has a Status column, the criteria of done tasks are due; without one, every criterion it names.
  const plans = docs.filter((d) => String(d.data.type || "") === "plan" && d.isLatest !== false && docStatus(d) !== "superseded");
  const compOf = (id) => { const c = classifyId(id); return c && c.kind === "criterion" ? componentOfPrefix(cfg, c.prefix) : undefined; };
  const due = new Map(); // component -> "all" or a Set of criterion IDs
  const addDue = (comp, ids) => {
    if (due.get(comp) === "all") return;
    if (ids === "all") return void due.set(comp, "all");
    if (!due.has(comp)) due.set(comp, new Set());
    for (const id of ids) due.get(comp).add(id);
  };
  for (const d of plans) {
    const comps = planComponents(d, cfg);
    const ofPlan = (text) => [...criteriaIn(text)].filter((id) => comps.includes(compOf(id)));
    const named = ofPlan(d.body);
    const delivered = (t, r) => t.headers.filter((h) => !NOT_DELIVERED.has(h)).map((h) => r[h]).join(" | ");
    const taskRows = parseTables(d.body).filter((t) => t.headers.includes("status"))
      .flatMap((t) => t.rows.map((r) => ({ status: r.status, ids: ofPlan(delivered(t, r)) }))).filter((r) => r.ids.length);
    for (const comp of comps) {
      if (!named.some((id) => compOf(id) === comp)) { addDue(comp, "all"); continue; }
      if (!taskRows.length) { addDue(comp, named.filter((id) => compOf(id) === comp)); continue; }
      addDue(comp, taskRows.filter((r) => DONE_STATUS.test(String(r.status).replace(/[`*_]/g, "").trim()))
        .flatMap((r) => r.ids).filter((id) => compOf(id) === comp));
    }
  }
  const inBuildCriterion = (comp, id) => { const v = due.get(comp); return v === "all" || (v instanceof Set && v.has(id)); };
  // Planned evidence: the test plan or the component's latest LLD names the criterion.
  const lldsFor = (comp) => docs.filter((d) => d.isLatest && String(d.data.type || "") === "lld" && docIsForComponent(d, cfg, comp));
  const mentions = (text, id) => new RegExp(`(^|[^A-Za-z0-9-])${id.replace(/[-]/g, "\\-")}(?![A-Za-z0-9-])`, "m").test(text || "");
  // Drift recorded by the verifier: components.<name>.drift as a list of criterion IDs
  const drifted = new Set();
  for (const comp of Object.values(index.components || {})) if (Array.isArray(comp.drift)) comp.drift.forEach((x) => drifted.add(String(x)));

  // Test results, when a JUnit report is given
  const resultsRel = results || cfg.paths.testResults;
  const junit = resultsRel ? readText(resolve(root, resultsRel)) : null;
  if (resultsRel && junit === null) warnings.push({ file: resultsRel, msg: "test report not found; passing and failing states are not shown" });
  const cases = junit ? readJUnit(junit) : null;

  // Index annotations
  const testsFor = new Map();
  const codeFor = new Map();
  for (const a of annotations) {
    for (const id of a.ids) {
      const map = a.isTest ? testsFor : codeFor;
      if (!map.has(id)) map.set(id, []);
      map.get(id).push(`${a.file}:${a.line}`);
      // 1. Reverse orphans: an annotation cites an ID that nothing defines
      if (!defs.has(id)) errors.push({ file: a.file, line: a.line, msg: `@spec ${id} cites an ID that no PRD defines (reverse orphan)` });
      else if (defs.get(id).kind !== "criterion")
        warnings.push({ file: a.file, line: a.line, msg: `@spec ${id} cites a ${defs.get(id).kind} ID; cite acceptance criteria instead` });
    }
  }

  // 2. Evidence for each acceptance criterion
  const rows = [];
  for (const def of defs.values()) {
    if (def.kind !== "criterion") continue;
    const tests = testsFor.get(def.id) || [];
    const code = codeFor.get(def.id) || [];
    const comp = componentOfPrefix(cfg, def.prefix);
    const building = inBuildCriterion(comp, def.id);
    const isApproved = def.docStatus === "approved";
    const planned = mentions(plan.body, def.id) || lldsFor(comp).some((d) => mentions(d.body, def.id));
    const ran = cases ? cases.filter((c) => mentions(c.name, def.id)) : [];
    let status;
    if (drifted.has(def.id)) status = "drifted";
    else if (tests.length && ran.length) status = ran.every((c) => c.passed) ? "passing" : "failing";
    else if (tests.length) status = "test linked";
    else if (deferred.has(def.id)) status = "deferred";
    else if (excepted.has(def.id)) status = "excepted";
    else if (planned) status = "planned";
    else status = "gap";

    if (deferred.has(def.id) && def.priority === "P1")
      errors.push({ file: def.file, line: def.line, msg: `${def.id} is P1 and cannot be deferred; record an exception (excepted:) if the owner accepts the risk` });
    if (!isApproved) {
      if (!tests.length && status !== "deferred" && status !== "excepted") infos.push({ msg: `${def.id} has no test yet (its PRD is ${def.docStatus || "unversioned"}, so this is not enforced)` });
      if (status === "gap" || status === "planned") status += " (draft)";
    } else if (status === "failing") {
      errors.push({ file: def.file, line: def.line, msg: `${def.id} has a failing test: ${ran.filter((c) => !c.passed).map((c) => c.name.trim()).join("; ")}` });
    } else if (status === "drifted") {
      warnings.push({ file: def.file, line: def.line, msg: `${def.id} has drift recorded in the trace index; the owner decides which artifact to correct` });
    } else if (status === "planned" || status === "gap") {
      if (building) errors.push({ file: def.file, line: def.line, msg: `${def.id} (${def.priority || "no priority"}) has no test citing it with @spec, and a milestone plan for ${comp} exists` });
      else if (status === "gap") warnings.push({ file: def.file, line: def.line, msg: `${def.id} has no planned evidence yet: map it to tests in the test plan or the ${comp} LLD before build` });
    }
    if (tests.length && !code.length)
      warnings.push({ file: def.file, line: def.line, msg: `${def.id} has a test but no code entry point carries @spec ${def.id}` });
    rows.push({ id: def.id, priority: def.priority, status, tests, code, file: def.file, component: comp });
  }
  for (const id of deferred) if (!defs.has(id)) warnings.push({ file: planRel, msg: `deferred ID ${id} is not defined` });
  for (const id of excepted) if (!defs.has(id)) warnings.push({ file: planRel, msg: `excepted ID ${id} is not defined` });

  // 3. Hollow status: the coverage report claims evidence that the annotations do not show
  const covText = readText(join(root, cfg.paths.coverage));
  if (covText && covText.includes(COVERAGE_START)) {
    const block = covText.slice(covText.indexOf(COVERAGE_START), covText.indexOf(COVERAGE_END));
    for (const line of block.split("\n")) {
      const m = /^\|\s*([A-Z][A-Z0-9-]*\d)\s*\|[^|]*\|\s*(covered|test linked|passing|failing)\s*\|/.exec(line);
      if (m && !(testsFor.get(m[1]) || []).length)
        errors.push({ file: cfg.paths.coverage, msg: `${m[1]} is marked ${m[2]} but no test cites it (hollow status); run trace-check --write` });
    }
  }

  // 4. Staleness from the trace index: source changes, and changes to the governing artifacts
  const now = Date.now();
  const gitOk = isGitRepo(root);
  for (const [name, comp] of Object.entries(index.components || {})) {
    const cfgComp = cfg.components[name] || {};
    const governing = governingArtifacts(docs, cfg, name);
    if (comp.audited) {
      const days = (now - Date.parse(comp.audited)) / 86400000;
      if (days > cfg.trace.staleAfterDays) warnings.push({ file: cfg.paths.traceIndex, msg: `component ${name} was last audited ${Math.floor(days)} days ago` });
      const approvedOn = (d) => (docStatus(d) === "approved" ? d.data.approved || d.data.date : null);
      const newer = governing.filter((d) => approvedOn(d) && Date.parse(String(approvedOn(d))) > Date.parse(comp.audited));
      if (newer.length) warnings.push({ file: cfg.paths.traceIndex, msg: `component ${name}: ${newer.map((d) => d.rel).join(", ")} was approved after the last audit` });
    } else warnings.push({ file: cfg.paths.traceIndex, msg: `component ${name} has never been audited` });
    if (gitOk && comp.audited_sha) {
      const paths = [...(cfgComp.paths || []), ...governing.map((d) => d.rel)];
      const changed = paths.length ? git(root, ["diff", "--name-only", `${comp.audited_sha}..HEAD`, "--", ...paths]) : null;
      if (changed) {
        const files = changed.split("\n");
        const upstream = files.filter((f) => governing.some((d) => d.rel === f));
        warnings.push({ file: cfg.paths.traceIndex, msg: `component ${name} changed since its last audit (${files.length} file(s)${upstream.length ? ", including " + upstream.join(", ") : ""})` });
      }
    }
  }

  // 5. Annotation reach (file level): changed source files that carry at least one @spec
  let reach = null;
  if (cfg.features.reachReport) {
    let files = listSourceFiles(root, cfg);
    if (base && gitOk) {
      const changed = git(root, ["diff", "--name-only", `${base}...HEAD`]);
      const set = new Set((changed || "").split("\n").filter(Boolean));
      files = files.filter((f) => set.has(f));
    }
    const annotated = new Set(annotations.filter((a) => !a.isTest).map((a) => a.file));
    const behavior = files.filter((f) => !/\.(d\.ts|md|json|ya?ml|lock|txt|css|svg|png)$/.test(f) && !/(^|\/)(index|types?)\.[a-z]+$/.test(f));
    if (behavior.length) {
      const hit = behavior.filter((f) => annotated.has(f)).length;
      reach = { files: behavior.length, annotated: hit, ratio: hit / behavior.length };
      const pct = Math.round(reach.ratio * 100);
      const msg = `annotation reach: ${hit} of ${behavior.length} ${base ? "changed " : ""}source file(s) carry @spec (${pct}%)`;
      if (reach.ratio < cfg.trace.reachWarnBelow) warnings.push({ msg });
      else infos.push({ msg });
    }
  }

  infos.push({ msg: `${rows.length} acceptance criteria, ${annotations.length} annotations` });
  return { errors, warnings, infos, rows, reach, index };
}

// The documents that govern a component: the parent PRD, its component PRD, the SPEC, its LLD
// and the test plan, latest versions only. Their versions are recorded with each audit.
export function governingArtifacts(docs, cfg, name) {
  return docs.filter((d) => {
    if (!d.isLatest) return false;
    const t = String(d.data.type || "");
    if (t === "prd" || t === "spec" || t === "test-plan") return true;
    if (t === "prd-component" || t === "lld") return docIsForComponent(d, cfg, name);
    return false;
  });
}

export function loadIndex(root, cfg) {
  const p = join(root, cfg.paths.traceIndex);
  if (!existsSync(p)) return { components: {} };
  return parseYaml(readFileSync(p, "utf8"));
}

export function coverageTable(rows) {
  const lines = [COVERAGE_START, "", "| ID | Priority | Evidence | Tests | Code entry points |", "| --- | --- | --- | --- | --- |"];
  for (const r of [...rows].sort((a, b) => a.id.localeCompare(b.id, "en", { numeric: true })))
    lines.push(`| ${r.id} | ${r.priority || ""} | ${r.status} | ${r.tests.join("<br>") || ""} | ${r.code.join("<br>") || ""} |`);
  lines.push("", `Generated by trace-check. Do not edit by hand.`, "", COVERAGE_END);
  return lines.join("\n");
}

// The audit record the verifier keeps per component, and the counts trace-check derives.
export const AUDIT_FIELDS = ["status", "scope", "owner", "sampled", "audited", "audited_sha", "findings", "disposition", "drift", "next"];
export const DERIVED_FIELDS = ["artifacts", "criteria", "linked", "passing", "failing", "planned", "deferred", "excepted", "drifted", "gaps"];

export function write(root, cfg, result) {
  const written = [];
  const covPath = join(root, cfg.paths.coverage);
  const header =
    "# Evidence for acceptance criteria\n\n" +
    "Derived status: which criteria have tests and code entry points citing them with `@spec`, and, when a test report is given, whether those tests pass. " +
    "Regenerated by `node tools/trace-check/trace-check.mjs --write`; never edit by hand. " +
    "Deferred and excepted criteria are listed in the test plan's front matter.\n\n" +
    "Evidence states: `test linked` (a test cites the criterion), `passing` or `failing` (a linked test ran), `planned` (mapped to tests in the test plan or LLD, not written yet), " +
    "`deferred`, `excepted`, `drifted` (recorded by the verifier) and `gap`. A link is structural: it does not prove that the test checks what the criterion means.\n\n";
  const next = header + coverageTable(result.rows) + "\n";
  if (readText(covPath) !== next) {
    mkdirSync(dirname(covPath), { recursive: true });
    writeFileSync(covPath, next);
    written.push(cfg.paths.coverage);
  }
  const idxPath = join(root, cfg.paths.traceIndex);
  if (existsSync(idxPath)) {
    const index = result.index || { components: {} };
    index.components = index.components || {};
    const allDocs = loadDocs(root, cfg);
    for (const [name, comp] of Object.entries(cfg.components)) {
      const mine = result.rows.filter((r) => r.component === name);
      const prev = index.components[name] || { status: "UNMAPPED" };
      const count = (...st) => mine.filter((r) => st.some((x) => r.status.startsWith(x))).length;
      // Verifier-owned audit record first, then the derived evidence counts.
      const entry = {};
      for (const k of AUDIT_FIELDS) if (k in prev) entry[k] = prev[k];
      for (const [k, v] of Object.entries(prev)) if (!AUDIT_FIELDS.includes(k) && !DERIVED_FIELDS.includes(k) && k !== "covered") entry[k] = v;
      Object.assign(entry, {
        artifacts: governingArtifacts(allDocs, cfg, name).map((d) => `${d.rel}@${docStatus(d) || "?"}`),
        criteria: mine.length,
        linked: count("test linked", "passing", "failing"),
        passing: count("passing"),
        failing: count("failing"),
        planned: count("planned"),
        deferred: count("deferred"),
        excepted: count("excepted"),
        drifted: count("drifted"),
        gaps: count("gap"),
      });
      index.components[name] = entry;
    }
    const header = readFileSync(idxPath, "utf8").split("\n").filter((l) => l.startsWith("#")).join("\n");
    const next = (header ? header + "\n" : "") + toYaml(index);
    if (next !== readFileSync(idxPath, "utf8")) {
      writeFileSync(idxPath, next);
      written.push(cfg.paths.traceIndex);
    }
  }
  return written;
}

if (isMain(import.meta.url)) {
  const args = parseArgs(process.argv.slice(2));
  const root = findRoot(args.root || process.cwd());
  try {
    const cfg = loadConfig(root);
    const result = analyze(root, cfg, {
      base: typeof args.base === "string" ? args.base : null,
      results: typeof args.results === "string" ? args.results : null,
    });
    if (args.write) {
      for (const w of write(root, cfg, result)) result.infos.push({ msg: `updated ${w}` });
      result.errors = result.errors.filter((e) => !e.msg.includes("hollow status"));
    }
    process.exit(report("trace-check", result, { json: !!args.json, advisory: !!args.advisory }));
  } catch (e) {
    console.error(`trace-check failed to run: ${e.message}`);
    process.exit(args.advisory ? 0 : 2);
  }
}
