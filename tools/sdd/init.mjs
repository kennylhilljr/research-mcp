// @ts-nocheck: plain JavaScript, kept out of the host project's type check
// sdd init: set up the framework in a brand-new (empty or nearly empty) repository.
import { existsSync, readFileSync } from "node:fs";
import { join, resolve, basename } from "node:path";
import { Plan, addMachinery, scaffoldText, EMPTY_DIRS, SCAFFOLD_FILES, FRAMEWORK_ROOT, today, isDirEmpty } from "./machinery.mjs";
import { FRAMEWORK_VERSION, git } from "../lib/sdd-lib.mjs";
import { writeDocmap } from "./docs.mjs";

export function parseComponents(spec) {
  // "tech:TECH,billing:BILL" -> { tech: { prefix: "TECH", paths: [...] } }
  const out = {};
  for (const part of String(spec || "").split(",").map((s) => s.trim()).filter(Boolean)) {
    const [name, prefix] = part.split(":");
    const n = name.toLowerCase().replace(/[^a-z0-9-]/g, "-");
    out[n] = { prefix: (prefix || n.slice(0, 4)).toUpperCase().replace(/[^A-Z0-9]/g, ""), paths: [`src/${n}`, `test/${n}`] };
  }
  return out;
}

export function planInit(target, opts = {}) {
  const dir = resolve(target);
  const name = opts.name || basename(dir);
  const components = parseComponents(opts.components);
  const vars = { PROJECT: name, DATE: today(), FRAMEWORK_VERSION, OWNER: opts.owner || "[Name]" };
  const plan = new Plan(dir);
  addMachinery(plan);
  for (const [to, from] of Object.entries(SCAFFOLD_FILES)) plan.file(to, scaffoldText(from, vars));
  plan.file(".github/workflows/ci.yml", scaffoldText("ci.yml", vars));
  plan.file(".github/CODEOWNERS", scaffoldText("CODEOWNERS", vars));
  plan.file(
    "sdd.config.json",
    JSON.stringify(
      {
        $schema: "./tools/sdd/sdd.config.schema.json",
        frameworkVersion: FRAMEWORK_VERSION,
        project: { name, description: "", scope: null },
        paths: { docs: "docs", codeRoots: ["src"], testRoots: ["test"], traceIndex: "docs/trace/index.yaml", coverage: "docs/trace/coverage.md", docMap: "docs/README.md", scopeMap: "docs/scope/scope-map.yaml" },
        approvals: { requireApprover: false },
        components,
        trace: { staleAfterDays: 30, reachWarnBelow: 0.8 },
        features: { gateHook: true, protectApprovedDocs: true, reachReport: true, divergenceProbe: false, differentialAudit: false },
      },
      null,
      2,
    ) + "\n",
  );
  if (!existsSync(join(dir, "package.json"))) plan.file("package.json", scaffoldText("package.json", { ...vars, PROJECT: name.toLowerCase().replace(/[^a-z0-9-]/g, "-") }));
  if (!existsSync(join(dir, ".gitignore"))) plan.file(".gitignore", scaffoldText("gitignore", vars));
  for (const d of [...EMPTY_DIRS, "src", "test"]) plan.dir(d);
  return plan;
}

export function runInit(target, opts = {}, log = console.log) {
  const dir = resolve(target || ".");
  if (dir === FRAMEWORK_ROOT) {
    log("sdd init: run this against a different folder, not the framework repository itself.");
    return 1;
  }
  if (!isDirEmpty(dir) && !opts.force) {
    log(`sdd init: ${dir} already has files. Use "sdd adopt" for an existing repository, or pass --force to add the framework anyway (existing files are never overwritten).`);
    return 1;
  }
  const plan = planInit(dir, opts);
  log(`sdd init ${opts.dryRun ? "(dry run) " : ""}-> ${dir}`);
  plan.print(log);
  if (opts.dryRun) return 0;
  plan.apply();
  writeDocmap(dir); // fill the generated views so CI's doc map check passes on the first run
  if (opts.git && git(dir, ["rev-parse", "--is-inside-work-tree"]) !== "true") git(dir, ["init", "-q"]);
  log("");
  log("Next steps:");
  log("  1. Edit AGENTS.md: fill in the owner, commands and any organization rules.");
  log("  2. Run the setup check:            node tools/sdd/cli.mjs doctor");
  log("  3. In Claude Code, start a spec:   /sdd-new <what you want to build>");
  log("  4. Read docs/guide/usage.md for the full workflow.");
  return 0;
}
