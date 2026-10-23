#!/usr/bin/env node
// @ts-nocheck: plain JavaScript, kept out of the host project's type check
// Gate hook (Claude Code PreToolUse, matcher "Skill").
// Blocks a skill until the artifact it builds on has passed its human gate.
// Exit 2 blocks the tool call and shows the reason to the agent; every other path exits 0,
// so a broken hook can never break a session.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { findRoot, loadConfig, loadDocs, docStatus, isMain, resolveComponent, docIsForComponent, planComponents } from "../lib/sdd-lib.mjs";

// skill -> the gate it waits for. Gates are approval checkpoints; they are not organizational
// scope levels (L0 to L3) and they are not document stages.
export const GATES = {
  "sdd-hld": { gate: 1, need: "an approved PRD (Gate 1)" },
  "sdd-lld": { gate: 2, need: "an approved SPEC (Gate 2) and an approved component PRD (Gate 1) for the component" },
  "sdd-tasks": { gate: 3, need: "an approved LLD (Gate 3) for the component" },
  "sdd-implement": { gate: 3, need: "a milestone plan whose components all have an approved LLD (Gate 3)" },
};

const OFF = "Turn the gate off with features.gateHook=false in sdd.config.json.";
const approved = (d) => docStatus(d) === "approved";

// Words right after the skill name: component names or prefixes (tech, TECH) and milestones (M1).
// Reading stops at the first other word, so "/sdd-lld tech, then leave billing alone" names only tech.
export function parseGateArgs(cfg, args) {
  const words = (Array.isArray(args) ? args : String(args || "").split(/[\s,]+/)).filter(Boolean);
  const components = [];
  const milestones = [];
  for (const w of words) {
    const c = resolveComponent(cfg, w);
    if (c) components.includes(c) || components.push(c);
    else if (/^M\d+$/i.test(w)) milestones.includes(w.toUpperCase()) || milestones.push(w.toUpperCase());
    else break;
  }
  return { components, milestones };
}

function block(gate, why, askOwner = true) {
  const ask = askOwner ? " Ask the owner to review the document and record the approval in its front matter (status: approved)." : "";
  return { allow: false, reason: `Gate ${gate} is not passed: ${why}${ask} ${OFF}` };
}

export function decide(root, skillName, args = []) {
  const name = String(skillName || "").replace(/^.*:/, "");
  const rule = GATES[name];
  if (!rule) return { allow: true };
  const cfg = loadConfig(root);
  if (!cfg.features.gateHook) return { allow: true };
  const docs = loadDocs(root, cfg);
  const configured = Object.keys(cfg.components);
  const named = parseGateArgs(cfg, args);
  let components = named.components;
  if (!components.length && configured.length === 1) components = configured;
  const ofType = (...types) => docs.filter((d) => types.includes(String(d.data.type || "")));
  const forComp = (list, c) => list.filter((d) => docIsForComponent(d, cfg, c));
  const needName = () =>
    block(rule.gate, `${name} works on one component, and this repository has ${configured.length} (${configured.join(", ")}). Name it, for example /${name} ${configured[0]}.`, false);

  if (name === "sdd-hld") {
    // The SPEC is system wide: any approved PRD opens Gate 1; a named component needs its own PRD approved.
    if (!ofType("prd", "prd-component").some(approved)) return block(1, `${name} needs ${rule.need}.`);
    for (const c of named.components)
      if (!forComp(ofType("prd-component"), c).some(approved)) return block(1, `the component PRD for ${c} is not approved.`);
    return { allow: true };
  }

  if (name === "sdd-lld") {
    if (!ofType("spec").some(approved)) return block(2, `${name} needs an approved SPEC, the system HLD.`);
    if (!components.length) return configured.length ? needName() : { allow: true };
    for (const c of components)
      if (!forComp(ofType("prd-component"), c).some(approved)) return block(1, `${name} for ${c} needs the ${c} component PRD approved first.`);
    return { allow: true };
  }

  if (name === "sdd-tasks") {
    if (!components.length) {
      if (configured.length) return needName();
      return ofType("lld").some(approved) ? { allow: true } : block(3, `${name} needs ${rule.need}.`);
    }
    for (const c of components)
      if (!forComp(ofType("lld"), c).some(approved)) return block(3, `${name} for ${c} needs the ${c} LLD approved.`);
    return { allow: true };
  }

  // sdd-implement: the plan, and the approved LLD behind each component the plan covers
  let plans = ofType("plan").filter((d) => d.isLatest && docStatus(d) !== "superseded");
  if (named.milestones.length) plans = plans.filter((d) => named.milestones.includes(String(d.data.milestone || "").toUpperCase()));
  if (named.components.length) plans = plans.filter((d) => planComponents(d, cfg).some((c) => named.components.includes(c)));
  if (!plans.length) return block(3, `${name} needs a milestone plan from sdd-tasks${named.milestones.length || named.components.length ? " for " + [...named.milestones, ...named.components].join(", ") : ""}.`, false);
  if (!named.milestones.length && plans.length > 1) {
    // Without a milestone, check the plans still open (no approved handoff yet); fall back to all of them.
    const done = new Set(ofType("handoff").filter(approved).map((d) => String(d.data.milestone || "").toUpperCase()));
    const open = plans.filter((d) => !done.has(String(d.data.milestone || "").toUpperCase()));
    if (open.length) plans = open;
  }
  const lld = ofType("lld");
  for (const p of plans) {
    const comps = planComponents(p, cfg);
    if (!configured.length && !comps.length) {
      if (!lld.some(approved)) return block(3, `${name} needs ${rule.need}.`);
      continue;
    }
    if (!comps.length) return block(3, `${p.rel} does not say which component it covers; add components: [..] to its front matter or cite the criteria it builds.`, false);
    for (const c of comps)
      if (!forComp(lld, c).some(approved))
        return block(3, `${p.rel} builds ${c}, and the ${c} LLD is not approved.${named.milestones.length ? "" : " Name the milestone to work on another plan, for example /sdd-implement M2."}`);
  }
  return { allow: true };
}

// Find which skill an event refers to. Two events are handled:
//   PreToolUse with tool_name "Skill" (the agent invokes a skill): the skill name is read from
//   tool_input.skill, or name or command when a client uses another field; and
//   UserPromptSubmit (a person types /sdd-lld ...).
export function skillFromEvent(input) {
  if (!input || typeof input !== "object") return null;
  if (input.hook_event_name === "UserPromptSubmit" || typeof input.prompt === "string") {
    const m = /^\s*\/(?:[a-z0-9-]+:)?(sdd-[a-z-]+)\b/.exec(String(input.prompt || ""));
    return m ? m[1] : null;
  }
  if (input.tool_name !== "Skill") return null;
  const ti = input.tool_input || {};
  const field = [ti.skill, ti.name, ti.command].find((v) => typeof v === "string" && v.trim());
  if (!field) return null;
  // "sdd-framework:sdd-lld", "/sdd-lld", "sdd-lld some args" -> "sdd-lld"
  const first = field.trim().replace(/^\//, "").split(/\s+/)[0];
  return first.replace(/^.*:/, "") || null;
}

// The arguments that came with the skill: the rest of a typed prompt, tool_input.args,
// or words after the skill name in the skill field.
export function argsFromEvent(input) {
  if (!input || typeof input !== "object") return [];
  const words = (s) => String(s || "").split(/[\s,]+/).filter(Boolean);
  if (input.hook_event_name === "UserPromptSubmit" || typeof input.prompt === "string")
    return words(String(input.prompt || "").replace(/^\s*\/\S+/, "").split("\n")[0]);
  const ti = input.tool_input || {};
  const field = [ti.skill, ti.name, ti.command].find((v) => typeof v === "string" && v.trim()) || "";
  return [...words(field).slice(1), ...words(typeof ti.args === "string" ? ti.args : Array.isArray(ti.args) ? ti.args.join(" ") : "")];
}

function main() {
  let input = {};
  try {
    input = JSON.parse(readFileSync(0, "utf8") || "{}");
  } catch {
    process.exit(0);
  }
  const skill = skillFromEvent(input);
  if (!skill) process.exit(0);
  const root = findRoot(process.env.CLAUDE_PROJECT_DIR || input.cwd || process.cwd());
  const result = decide(root, skill, argsFromEvent(input));
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
