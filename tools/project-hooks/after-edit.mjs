#!/usr/bin/env node
// @ts-nocheck: plain JavaScript, kept out of the host project's type check
// After-edit hook (Claude Code PostToolUse, matcher "Edit|Write|MultiEdit").
// Project-only tooling: after a .py edit under src/ or tests/ it runs ruff (safe
// fixes, format, check), mypy for src/ edits, and the pytest files mapped to the
// edited module. Exit 2 reports every failed step on stderr; every other path
// exits 0. RESEARCH_MCP_EDIT_HOOK=off makes it exit 0 with no output at all.
import { readFileSync, existsSync, readdirSync, realpathSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { resolve, relative, isAbsolute, join, sep } from "node:path";
import { fileURLToPath } from "node:url";

const TOOLS = new Set(["Edit", "Write", "MultiEdit"]);
const TIMEOUT_MS = 90000;
const TAIL_LINES = 60;

const HIGH_RISK = new Set([
  "src/research_mcp/platform/secrets.py",
  "src/research_mcp/platform/redact.py",
  "src/research_mcp/platform/http.py",
  "src/research_mcp/platform/stores.py",
  "src/research_mcp/app.py",
  "src/research_mcp/shim.py",
]);

const CONTRACT = new Set([
  "src/research_mcp/core/models.py",
  "src/research_mcp/core/envelope.py",
  "src/research_mcp/core/errors.py",
]);

function escapeRegExp(s) {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

// Root-relative test files in `dir` whose name starts with test_<prefix>.
function matching(fsLookup, dir, prefix) {
  const re = new RegExp(`^test_${escapeRegExp(prefix)}.*\\.py$`);
  return fsLookup
    .listDir(dir)
    .filter((name) => re.test(name))
    .sort()
    .map((name) => `${dir}/${name}`);
}

// Map a root-relative .py path to the pytest targets that cover it.
// fsLookup answers root-relative paths, so the result never depends on process.cwd().
export function testsFor(relPath, fsLookup) {
  const out = [];
  if (relPath.startsWith("tests/") && relPath.endsWith(".py")) {
    out.push(relPath);
  } else {
    const source = relPath.match(/^src\/research_mcp\/sources\/([^/]+)\.py$/);
    const nested = relPath.match(/^src\/research_mcp\/([^/]+)\/([^/]+)\.py$/);
    const top = relPath.match(/^src\/research_mcp\/([^/]+)\.py$/);
    if (source) {
      const name = source[1];
      if (fsLookup.exists(`tests/sources/${name}/`)) out.push(`tests/sources/${name}/`);
      out.push(...matching(fsLookup, "tests/unit/sources", name));
      out.push("tests/unit/sources/test_adapter_imports.py");
    } else if (nested) {
      const [, pkg, module] = nested;
      out.push(...matching(fsLookup, `tests/unit/${pkg}`, module));
      out.push(...matching(fsLookup, `tests/${pkg}`, module));
    } else if (top) {
      out.push(...matching(fsLookup, "tests/unit", top[1]));
      out.push(...matching(fsLookup, "tests/integration", top[1]));
    }
    if (HIGH_RISK.has(relPath)) out.push("tests/security/");
    if (relPath.startsWith("src/research_mcp/mcp_app/") || CONTRACT.has(relPath)) out.push("tests/contract/");
  }
  return [...new Set(out)].filter((p) => fsLookup.exists(p));
}

function note(text) {
  return { code: 0, stdout: `after-edit: ${text}\n`, stderr: "", calls: [] };
}

function tail(text, n) {
  const lines = text.replace(/\n+$/, "").split("\n");
  return lines.slice(-n).join("\n");
}

function makeFsLookup(root) {
  return {
    exists: (p) => existsSync(join(root, p)),
    listDir: (p) => {
      try {
        return readdirSync(join(root, p));
      } catch {
        return [];
      }
    },
  };
}

function defaultPreflight(root) {
  const uv = spawnSync("uv", ["--version"], { cwd: root, encoding: "utf8", timeout: 10000 });
  if (uv.error || uv.status !== 0) return { ok: false, missing: "uv" };
  if (!existsSync(join(root, ".venv"))) return { ok: false, missing: ".venv" };
  return { ok: true };
}

function defaultRunner(cmd, args, options) {
  const r = spawnSync(cmd, args, {
    cwd: options.cwd,
    timeout: options.timeout,
    encoding: "utf8",
    maxBuffer: 64 * 1024 * 1024,
  });
  const timedOut = r.error?.code === "ETIMEDOUT";
  const spawnError = r.error && !timedOut ? `${r.error.message}\n` : "";
  return { status: r.status, stdout: r.stdout || "", stderr: (r.stderr || "") + spawnError, timedOut };
}

// Drive the whole hook through injected collaborators. Reads no process.env and no stdin.
export function handle(input, env, { runner = defaultRunner, fsLookup, preflight = defaultPreflight } = {}) {
  if (env.RESEARCH_MCP_EDIT_HOOK === "off") return { code: 0, stdout: "", stderr: "", calls: [] };

  let parsed;
  try {
    parsed = JSON.parse(input);
  } catch {
    return note("ignored: stdin is not valid JSON");
  }
  if (!parsed || typeof parsed !== "object") return note("ignored: stdin is not a JSON object");
  if (!TOOLS.has(parsed.tool_name)) return note(`ignored: tool ${JSON.stringify(parsed.tool_name ?? null)} is not Edit, Write or MultiEdit`);
  const filePath = parsed.tool_input?.file_path;
  if (filePath === undefined || filePath === null) return note("ignored: tool_input.file_path is missing");
  if (typeof filePath !== "string") return note("ignored: tool_input.file_path is not a string");
  if (filePath === "") return note("ignored: tool_input.file_path is empty");
  if (!filePath.endsWith(".py")) return note(`ignored: ${filePath} is not a Python file`);

  const root = resolve(env.CLAUDE_PROJECT_DIR || parsed.cwd || process.cwd());
  const absPath = resolve(root, filePath);
  const relPath = relative(root, absPath).split(sep).join("/");
  if (isAbsolute(relPath) || !(relPath.startsWith("src/") || relPath.startsWith("tests/"))) {
    return note(`ignored: ${relPath} is outside src/ and tests/`);
  }

  const calls = [];
  try {
    const ready = preflight(root);
    if (!ready.ok) {
      return note(`skipped: ${ready.missing === ".venv" ? `.venv is missing in ${root} (run uv sync --frozen)` : "uv is not installed or not on PATH"}`);
    }

    const steps = [
      ["ruff fix", ["ruff", "check", "--fix", "--force-exclude", absPath]],
      ["ruff format", ["ruff", "format", "--force-exclude", absPath]],
      ["ruff check", ["ruff", "check", "--force-exclude", absPath]],
    ];
    if (relPath.startsWith("src/")) steps.push(["mypy", ["mypy"]]);
    const targets = testsFor(relPath, fsLookup ?? makeFsLookup(root));
    if (targets.length > 0) steps.push(["pytest", ["pytest", "-q", "-x", ...targets]]);

    const failures = [];
    for (const [name, toolArgs] of steps) {
      const args = ["run", "--no-sync", ...toolArgs];
      const options = { cwd: root, timeout: TIMEOUT_MS };
      calls.push({ cmd: "uv", args, options });
      const r = runner("uv", args, options);
      if (r.timedOut || r.status !== 0) {
        const command = ["uv", ...args].join(" ");
        const header = `after-edit: ${name} failed${r.timedOut ? " (timed out after 90 s)" : ""}: ${command}`;
        const output = tail(`${r.stdout || ""}${r.stderr || ""}`, TAIL_LINES);
        failures.push(output ? `${header}\n${output}\n` : `${header}\n`);
      }
    }

    if (failures.length > 0) return { code: 2, stdout: "", stderr: failures.join(""), calls };
    const ran = steps.map(([name]) => name).join(", ");
    const tests = targets.length > 0 ? `pytest targets: ${targets.join(" ")}` : "no tests mapped";
    return { code: 0, stdout: `after-edit: ok ${relPath}: ${ran}; ${tests}\n`, stderr: "", calls };
  } catch (err) {
    return { ...note(`unexpected error, checks not run: ${String(err?.message ?? err).split("\n")[0]}`), calls };
  }
}

function isMain() {
  try {
    return realpathSync(process.argv[1]) === realpathSync(fileURLToPath(import.meta.url));
  } catch {
    return false;
  }
}

function main() {
  const input = process.env.RESEARCH_MCP_EDIT_HOOK === "off" ? "" : readFileSync(0, "utf8");
  const result = handle(input, process.env);
  if (result.stdout) process.stdout.write(result.stdout);
  if (result.stderr) process.stderr.write(result.stderr);
  process.exitCode = result.code;
}

if (isMain()) {
  try {
    main();
  } catch (err) {
    if (process.env.RESEARCH_MCP_EDIT_HOOK !== "off") {
      process.stdout.write(`after-edit: unexpected error, checks not run: ${String(err?.message ?? err).split("\n")[0]}\n`);
    }
    process.exitCode = 0;
  }
}
