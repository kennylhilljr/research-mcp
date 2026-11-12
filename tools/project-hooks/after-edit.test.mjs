// @ts-nocheck: plain JavaScript, kept out of the host project's type check
// Tests for the after-edit hook. Hermetic: every collaborator is a fake, nothing
// real is spawned, and the only files written live under os.tmpdir().
import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, writeFileSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { handle, testsFor } from "./after-edit.mjs";

const ROOT = resolve(tmpdir(), "after-edit-fixture-root");

// The fixture inventory: root-relative files. A folder exists when any file sits under it.
const INVENTORY = [
  "src/research_mcp/cli.py",
  "src/research_mcp/app.py",
  "src/research_mcp/sources/arxiv.py",
  "src/research_mcp/sources/sitequery.py",
  "src/research_mcp/sources/registry.py",
  "src/research_mcp/sources/base.py",
  "src/research_mcp/platform/download.py",
  "src/research_mcp/platform/redact.py",
  "src/research_mcp/mcp_app/server.py",
  "src/research_mcp/core/models.py",
  "src/research_mcp/core/lonely.py",
  "src/research_mcp/services/works.py",
  "tests/sources/arxiv/test_search.py",
  "tests/unit/sources/test_adapter_imports.py",
  "tests/unit/sources/test_registry.py",
  "tests/unit/sources/test_sitequery.py",
  "tests/unit/sources/test_arxivextra.py",
  "tests/unit/platform/test_downloader.py",
  "tests/unit/platform/test_redact.py",
  "tests/unit/platform/test_http.py",
  "tests/unit/core/test_models.py",
  "tests/unit/test_cli.py",
  "tests/services/test_works.py",
  "tests/security/test_no_secrets.py",
  "tests/contract/test_tools.py",
];

function makeFsLookup(files = INVENTORY) {
  const set = new Set(files);
  return {
    exists(p) {
      if (set.has(p)) return true;
      const dir = p.endsWith("/") ? p : p + "/";
      return files.some((f) => f.startsWith(dir));
    },
    listDir(p) {
      const dir = p.endsWith("/") ? p : p + "/";
      const names = new Set();
      for (const f of files) if (f.startsWith(dir)) names.add(f.slice(dir.length).split("/")[0]);
      return [...names];
    },
  };
}

function okPreflight() {
  return { ok: true };
}

// A fake runner that records every call and answers from a per-step script.
function makeRunner(answer = () => ({ status: 0, stdout: "", stderr: "", timedOut: false })) {
  const calls = [];
  const runner = (cmd, args, options) => {
    calls.push({ cmd, args, options });
    return { status: 0, stdout: "", stderr: "", timedOut: false, ...answer(cmd, args, options) };
  };
  return { runner, calls };
}

function editInput(filePath, toolName = "Edit") {
  return JSON.stringify({ tool_name: toolName, tool_input: { file_path: filePath } });
}

const ENV = { CLAUDE_PROJECT_DIR: ROOT };

function line(call) {
  return [call.cmd, ...call.args].join(" ");
}

function stepOf(args) {
  const tool = args[2];
  if (tool === "ruff" && args[3] === "format") return "ruff format";
  if (tool === "ruff" && args.includes("--fix")) return "ruff fix";
  if (tool === "ruff") return "ruff check";
  return tool;
}

function assertOneNote(result) {
  assert.equal(result.code, 0);
  const lines = result.stdout.trim().split("\n");
  assert.equal(lines.length, 1, `expected one line, got ${JSON.stringify(result.stdout)}`);
  assert.ok(lines[0].startsWith("after-edit:"), lines[0]);
}

// AC1: diagnostic notes, zero runner calls.
const IGNORED = [
  ["invalid JSON", "not json", okPreflight],
  ["missing file_path", JSON.stringify({ tool_name: "Edit", tool_input: {} }), okPreflight],
  ["non-string file_path", JSON.stringify({ tool_name: "Edit", tool_input: { file_path: 5 } }), okPreflight],
  ["ignored tool_name", JSON.stringify({ tool_name: "Read", tool_input: { file_path: "src/research_mcp/cli.py" } }), okPreflight],
  ["README.md", editInput("README.md"), okPreflight],
  ["out-of-scope .py", editInput("tools/gen_inventory.py", "Write"), okPreflight],
  ["uv missing", editInput("src/research_mcp/cli.py"), () => ({ ok: false, missing: "uv" })],
  [".venv missing", editInput("src/research_mcp/cli.py"), () => ({ ok: false, missing: ".venv" })],
];

for (const [name, input, preflight] of IGNORED) {
  test(`AC1: ${name} prints one after-edit: note, exits 0 and runs nothing`, () => {
    const { runner, calls } = makeRunner();
    const result = handle(input, ENV, { runner, fsLookup: makeFsLookup(), preflight });
    assertOneNote(result);
    assert.equal(result.stderr, "");
    assert.equal(calls.length, 0);
  });
}

test("AC1: a runner that throws takes the unexpected-error path", () => {
  const calls = [];
  const runner = (cmd, args, options) => {
    calls.push({ cmd, args, options });
    throw new Error("boom");
  };
  const result = handle(editInput("src/research_mcp/cli.py"), ENV, {
    runner,
    fsLookup: makeFsLookup(),
    preflight: okPreflight,
  });
  assert.equal(calls.length, 1);
  assertOneNote(result);
  assert.match(result.stdout, /boom/);
  assert.equal(result.stderr, "");
});

test("AC2: RESEARCH_MCP_EDIT_HOOK=off is completely silent and touches nothing", () => {
  const dir = mkdtempSync(join(tmpdir(), "after-edit-off-"));
  try {
    const sample = join(dir, "sample.py");
    writeFileSync(sample, "x=1\n");
    const before = readFileSync(sample);
    const env = { CLAUDE_PROJECT_DIR: dir, RESEARCH_MCP_EDIT_HOOK: "off" };
    for (const input of ["not json", editInput("src/research_mcp/cli.py"), editInput(sample)]) {
      const { runner, calls } = makeRunner();
      let preflightCalls = 0;
      const result = handle(input, env, {
        runner,
        fsLookup: makeFsLookup(),
        preflight: () => {
          preflightCalls += 1;
          return { ok: true };
        },
      });
      assert.deepEqual(result.code, 0);
      assert.equal(result.stdout, "");
      assert.equal(result.stderr, "");
      assert.equal(calls.length, 0);
      assert.equal(preflightCalls, 0);
    }
    assert.deepEqual(readFileSync(sample), before);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test("AC3: a src/ edit runs ruff fix, format, check, mypy and pytest in order", () => {
  const rel = "src/research_mcp/platform/redact.py";
  const abs = resolve(ROOT, rel);
  const { runner, calls } = makeRunner();
  const result = handle(editInput(rel), ENV, { runner, fsLookup: makeFsLookup(), preflight: okPreflight });
  assert.equal(result.code, 0, result.stderr);
  const targets = testsFor(rel, makeFsLookup());
  assert.ok(targets.includes("tests/security/"));
  assert.deepEqual(calls.map(line), [
    `uv run --no-sync ruff check --fix --force-exclude ${abs}`,
    `uv run --no-sync ruff format --force-exclude ${abs}`,
    `uv run --no-sync ruff check --force-exclude ${abs}`,
    "uv run --no-sync mypy",
    `uv run --no-sync pytest -q -x ${targets.join(" ")}`,
  ]);
  for (const call of calls) {
    assert.equal(call.options.cwd, ROOT);
    assert.ok(!call.args.includes("--unsafe-fixes"));
  }
  const lines = result.stdout.trim().split("\n");
  assert.equal(lines.length, 1);
  assert.ok(lines[0].startsWith("after-edit:"));
  assert.match(lines[0], /tests\/security\//);
  assert.equal(result.stderr, "");
});

test("AC3: an absolute file_path is made root-relative", () => {
  const rel = "src/research_mcp/cli.py";
  const { runner, calls } = makeRunner();
  const result = handle(editInput(resolve(ROOT, rel)), ENV, { runner, fsLookup: makeFsLookup(), preflight: okPreflight });
  assert.equal(result.code, 0, result.stderr);
  assert.equal(line(calls.at(-1)), "uv run --no-sync pytest -q -x tests/unit/test_cli.py");
});

test("AC3: a tests/ edit skips mypy and runs only that test file", () => {
  const rel = "tests/unit/platform/test_http.py";
  const { runner, calls } = makeRunner();
  const result = handle(editInput(rel), ENV, { runner, fsLookup: makeFsLookup(), preflight: okPreflight });
  assert.equal(result.code, 0, result.stderr);
  assert.ok(!calls.some((c) => c.args.includes("mypy")));
  const pytest = calls.filter((c) => c.args.includes("pytest"));
  assert.equal(pytest.length, 1);
  assert.deepEqual(pytest[0].args.slice(5), [rel]);
});

test("AC3: a module with no tests runs no pytest and says so", () => {
  const { runner, calls } = makeRunner();
  const result = handle(editInput("src/research_mcp/core/lonely.py"), ENV, {
    runner,
    fsLookup: makeFsLookup(),
    preflight: okPreflight,
  });
  assert.equal(result.code, 0);
  assert.equal(calls.length, 4);
  assert.ok(!calls.some((c) => c.args.includes("pytest")));
  assert.match(result.stdout, /no tests mapped/);
  assert.equal(result.stdout.trim().split("\n").length, 1);
});

test("AC4: every step gets a 90000 ms timeout and a timeout is a reported failure", () => {
  const { runner, calls } = makeRunner((cmd, args) =>
    stepOf(args) === "ruff format" ? { status: null, timedOut: true, stdout: "slow\n" } : {},
  );
  const result = handle(editInput("src/research_mcp/platform/redact.py"), ENV, {
    runner,
    fsLookup: makeFsLookup(),
    preflight: okPreflight,
  });
  for (const call of calls) assert.equal(call.options.timeout, 90000);
  assert.deepEqual(calls.map((c) => stepOf(c.args)), ["ruff fix", "ruff format", "ruff check", "mypy", "pytest"]);
  assert.equal(result.code, 2);
  assert.equal(result.stdout, "");
  const header = result.stderr.split("\n").find((l) => l.includes("ruff format"));
  assert.ok(header, result.stderr);
  assert.match(header, /timed out/);
});

test("AC5: every failing step is reported with its own output tail", () => {
  const failing = { "ruff check": "E501 line too long", mypy: "error: bad type", pytest: "1 failed" };
  const { runner, calls } = makeRunner((cmd, args) => {
    const out = failing[stepOf(args)];
    return out ? { status: 1, stdout: `${out}\n` } : {};
  });
  const result = handle(editInput("src/research_mcp/platform/redact.py"), ENV, {
    runner,
    fsLookup: makeFsLookup(),
    preflight: okPreflight,
  });
  assert.equal(calls.length, 5);
  assert.equal(result.code, 2);
  for (const [step, out] of Object.entries(failing)) {
    const at = result.stderr.indexOf(`after-edit: ${step} failed`);
    assert.ok(at >= 0, `missing header for ${step}: ${result.stderr}`);
    assert.ok(result.stderr.indexOf(out, at) > at, `missing tail for ${step}`);
  }
  assert.ok(!result.stderr.includes("ruff format failed"));
});

test("AC5: a long output keeps only the last 60 lines", () => {
  const big = Array.from({ length: 200 }, (_, i) => `line-${i}`).join("\n");
  const { runner } = makeRunner((cmd, args) => (stepOf(args) === "mypy" ? { status: 1, stdout: big } : {}));
  const result = handle(editInput("src/research_mcp/cli.py"), ENV, {
    runner,
    fsLookup: makeFsLookup(),
    preflight: okPreflight,
  });
  assert.equal(result.code, 2);
  assert.ok(result.stderr.includes("line-199"));
  assert.ok(!result.stderr.includes("line-139\n"));
});

test("AC5: a ruff fix failure does not stop the later steps", () => {
  const { runner, calls } = makeRunner((cmd, args) => (stepOf(args) === "ruff fix" ? { status: 1, stderr: "fix broke" } : {}));
  const result = handle(editInput("src/research_mcp/cli.py"), ENV, {
    runner,
    fsLookup: makeFsLookup(),
    preflight: okPreflight,
  });
  assert.deepEqual(calls.map((c) => stepOf(c.args)), ["ruff fix", "ruff format", "ruff check", "mypy", "pytest"]);
  assert.equal(result.code, 2);
  assert.match(result.stderr, /after-edit: ruff fix failed: uv run --no-sync ruff check --fix --force-exclude /);
  assert.match(result.stderr, /fix broke/);
});

// AC6: testsFor against the fixture inventory.
const fs = makeFsLookup();

test("AC6: sources/arxiv.py maps to its folder, prefix matches and the import test", () => {
  const t = testsFor("src/research_mcp/sources/arxiv.py", fs);
  assert.ok(t.includes("tests/sources/arxiv/"));
  assert.ok(t.includes("tests/unit/sources/test_adapter_imports.py"));
  assert.ok(t.includes("tests/unit/sources/test_arxivextra.py"));
});

test("AC6: sources/sitequery.py without a folder maps to its unit test", () => {
  const t = testsFor("src/research_mcp/sources/sitequery.py", fs);
  assert.ok(t.includes("tests/unit/sources/test_sitequery.py"));
  assert.ok(t.includes("tests/unit/sources/test_adapter_imports.py"));
  assert.ok(!t.includes("tests/sources/sitequery/"));
});

test("AC6: sources/registry.py and sources/base.py are not excluded", () => {
  const reg = testsFor("src/research_mcp/sources/registry.py", fs);
  assert.ok(reg.includes("tests/unit/sources/test_registry.py"));
  assert.ok(reg.includes("tests/unit/sources/test_adapter_imports.py"));
  assert.deepEqual(testsFor("src/research_mcp/sources/base.py", fs), ["tests/unit/sources/test_adapter_imports.py"]);
});

test("AC6: platform/download.py finds test_downloader.py by prefix", () => {
  assert.deepEqual(testsFor("src/research_mcp/platform/download.py", fs), ["tests/unit/platform/test_downloader.py"]);
});

test("AC6: platform/redact.py appends tests/security/", () => {
  assert.deepEqual(testsFor("src/research_mcp/platform/redact.py", fs), [
    "tests/unit/platform/test_redact.py",
    "tests/security/",
  ]);
});

test("AC6: mcp_app and core contract modules append tests/contract/", () => {
  assert.ok(testsFor("src/research_mcp/mcp_app/server.py", fs).includes("tests/contract/"));
  assert.deepEqual(testsFor("src/research_mcp/core/models.py", fs), ["tests/unit/core/test_models.py", "tests/contract/"]);
});

test("AC6: services/works.py maps to tests/services/test_works.py", () => {
  assert.deepEqual(testsFor("src/research_mcp/services/works.py", fs), ["tests/services/test_works.py"]);
});

test("AC6: a top-level module maps to tests/unit", () => {
  assert.deepEqual(testsFor("src/research_mcp/cli.py", fs), ["tests/unit/test_cli.py"]);
});

test("AC6: a tests file maps to itself", () => {
  assert.deepEqual(testsFor("tests/unit/platform/test_http.py", fs), ["tests/unit/platform/test_http.py"]);
});

test("AC6: a module with no tests maps to nothing", () => {
  assert.deepEqual(testsFor("src/research_mcp/core/lonely.py", fs), []);
});

test("AC6: targets missing from the inventory are filtered out", () => {
  const noSecurity = makeFsLookup(INVENTORY.filter((f) => !f.startsWith("tests/security/")));
  assert.deepEqual(testsFor("src/research_mcp/platform/redact.py", noSecurity), ["tests/unit/platform/test_redact.py"]);
  const noImports = makeFsLookup(INVENTORY.filter((f) => !f.endsWith("test_adapter_imports.py")));
  assert.deepEqual(testsFor("src/research_mcp/sources/base.py", noImports), []);
  assert.deepEqual(testsFor("tests/unit/test_gone.py", fs), []);
});

test("AC6: results stay root-relative after process.chdir", () => {
  const before = process.cwd();
  try {
    process.chdir(tmpdir());
    assert.deepEqual(testsFor("src/research_mcp/cli.py", fs), ["tests/unit/test_cli.py"]);
    assert.ok(testsFor("src/research_mcp/sources/arxiv.py", fs).includes("tests/sources/arxiv/"));
  } finally {
    process.chdir(before);
  }
});
