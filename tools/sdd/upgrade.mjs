// @ts-nocheck: plain JavaScript, kept out of the host project's type check
// sdd upgrade: bring a newer framework release into a repository that already uses the framework.
//
// Only framework-owned files are considered (skills, personas, commands, tools, templates, standards,
// guides, framework diagrams). Project documents, AGENTS.md, CLAUDE.md, settings and config are never
// touched. Dry run by default.
//   --apply              create missing framework files; for files that differ, write the new release's
//                        version to .sdd-proposed/<path> for review
//   --apply --overwrite  replace differing framework files in place (use when you have not customized them)
import { existsSync, readFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { Plan, machineryFiles, FRAMEWORK_ROOT } from "./machinery.mjs";
import { FRAMEWORK_VERSION, isGitRepo, git } from "../lib/sdd-lib.mjs";

export function planUpgrade(target, { overwrite = false } = {}) {
  const plan = new Plan(target);
  for (const r of machineryFiles()) plan.copy(join(FRAMEWORK_ROOT, r), r, { onConflict: overwrite ? "overwrite" : "propose" });
  return plan;
}

export function runUpgrade(target, opts = {}, log = console.log) {
  const dir = resolve(target || ".");
  if (dir === FRAMEWORK_ROOT) {
    log("sdd upgrade: run this against a repository that uses the framework, not the framework repository itself.");
    return 1;
  }
  const cfgPath = join(dir, "sdd.config.json");
  if (!existsSync(cfgPath)) {
    log(`sdd upgrade: ${dir} does not use the framework yet. Use "sdd init" for a new repository or "sdd adopt" for an existing one.`);
    return 1;
  }
  let current = "unknown";
  try {
    current = JSON.parse(readFileSync(cfgPath, "utf8")).frameworkVersion || "unknown";
  } catch {
    /* keep unknown */
  }
  if (opts.apply && isGitRepo(dir) && (git(dir, ["status", "--porcelain"]) || "").length && !opts["allow-dirty"]) {
    log("sdd upgrade: the working tree has uncommitted changes. Commit or stash them first, or pass --allow-dirty.");
    return 1;
  }
  const plan = planUpgrade(dir, { overwrite: !!opts.overwrite });
  log(`sdd upgrade ${opts.apply ? "" : "(dry run: nothing will be written) "}${current} -> ${FRAMEWORK_VERSION} in ${dir}`);
  plan.print(log);
  if (!opts.apply) {
    log("\nRe-run with --apply to write. Differing files go to .sdd-proposed/ unless you add --overwrite.");
    return 0;
  }
  plan.apply();
  log("\nDone. Next steps:");
  log("  1. Review .sdd-proposed/ and merge what you want, then delete that folder.");
  log(`  2. Set "frameworkVersion": "${FRAMEWORK_VERSION}" in sdd.config.json.`);
  log("  3. Run: node tools/sdd/cli.mjs catalog && node tools/sdd/cli.mjs check");
  return 0;
}
