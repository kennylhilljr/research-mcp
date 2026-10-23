// @ts-nocheck: plain JavaScript, kept out of the host project's type check
// sdd adopt: analyze an existing, running application and add the framework without breaking it.
//
// Safety rules (tested in test/tools/setup.test.ts):
//   - dry run by default: nothing is written unless --apply is passed
//   - existing files are never modified or deleted; for a conflicting file the framework's version goes to .sdd-proposed/<path>
//   - the application's own commands (build, test, install) are never run
//   - CI is added as a separate, advisory workflow that cannot fail existing pipelines
import { existsSync, readFileSync, readdirSync } from "node:fs";
import { join, resolve, basename, extname } from "node:path";
import { Plan, addMachinery, scaffoldText, EMPTY_DIRS, FRAMEWORK_ROOT, today } from "./machinery.mjs";
import { walk, rel, readText, isBinary, git, isGitRepo, FRAMEWORK_VERSION, SPEC_ANNOTATION_RE, toYaml } from "../lib/sdd-lib.mjs";

const LANGS = {
  ".ts": "TypeScript", ".tsx": "TypeScript", ".js": "JavaScript", ".jsx": "JavaScript", ".mjs": "JavaScript", ".cjs": "JavaScript",
  ".py": "Python", ".go": "Go", ".rs": "Rust", ".java": "Java", ".kt": "Kotlin", ".cs": "C#", ".rb": "Ruby", ".php": "PHP",
  ".swift": "Swift", ".scala": "Scala", ".c": "C", ".cpp": "C++", ".h": "C/C++", ".sql": "SQL", ".sh": "Shell",
};
const MANIFESTS = {
  "package.json": "npm", "pnpm-lock.yaml": "pnpm", "yarn.lock": "yarn", "bun.lockb": "bun", "requirements.txt": "pip",
  "pyproject.toml": "Python (pyproject)", "Pipfile": "pipenv", "go.mod": "Go modules", "Cargo.toml": "Cargo", "pom.xml": "Maven",
  "build.gradle": "Gradle", "build.gradle.kts": "Gradle", "Gemfile": "Bundler", "composer.json": "Composer",
};
const FRAMEWORK_HINTS = [
  ["next", "Next.js"], ["react", "React"], ["vue", "Vue"], ["@angular/core", "Angular"], ["express", "Express"], ["fastify", "Fastify"],
  ["@nestjs/core", "NestJS"], ["koa", "Koa"], ["django", "Django"], ["flask", "Flask"], ["fastapi", "FastAPI"], ["spring-boot", "Spring Boot"],
  ["gin-gonic", "Gin"], ["rails", "Rails"], ["laravel", "Laravel"],
];
const TEST_HINTS = [["vitest", "Vitest"], ["jest", "Jest"], ["mocha", "Mocha"], ["pytest", "pytest"], ["junit", "JUnit"], ["playwright", "Playwright"], ["cypress", "Cypress"], ["rspec", "RSpec"]];
const INTEGRATION_HINTS = [
  ["pg", "PostgreSQL"], ["postgres", "PostgreSQL"], ["psycopg", "PostgreSQL"], ["mysql", "MySQL"], ["mongodb", "MongoDB"], ["mongoose", "MongoDB"],
  ["redis", "Redis"], ["ioredis", "Redis"], ["kafkajs", "Kafka"], ["kafka", "Kafka"], ["amqplib", "RabbitMQ"], ["@aws-sdk", "AWS"], ["boto3", "AWS"],
  ["@google-cloud", "Google Cloud"], ["@azure", "Azure"], ["stripe", "Stripe"], ["prisma", "Prisma"], ["sequelize", "Sequelize"], ["typeorm", "TypeORM"],
  ["sqlalchemy", "SQLAlchemy"], ["elasticsearch", "Elasticsearch"], ["@opentelemetry", "OpenTelemetry"], ["sentry", "Sentry"],
];
// folders that hold plumbing rather than a domain; never proposed as components
const NON_DOMAIN_DIRS = new Set(["test", "tests", "__tests__", "spec", "specs", "e2e", "assets", "static", "public", "styles", "migrations",
  "prisma", "db", "database", "config", "configs", "types", "typings", "utils", "util", "helpers", "common", "shared", "models", "mocks",
  "__mocks__", "fixtures", "scripts", "generated", "__generated__", "i18n", "locales", "vendor", "internal-tools"]);
// folders that group domains; components are looked for one level below them
const WRAPPER_DIRS = new Set(["routes", "modules", "features", "domains", "services", "controllers", "handlers", "api", "apps", "packages", "components", "pages"]);
const SOURCE_ROOT_CANDIDATES = ["src", "app", "lib", "pkg", "internal", "cmd", "server", "client", "api", "services", "packages", "apps", "backend", "frontend"];
const TEST_ROOT_CANDIDATES = ["test", "tests", "__tests__", "spec", "e2e"];

export function analyzeRepo(target) {
  const dir = resolve(target);
  const files = walk(dir, { maxFiles: 30000 }).map((f) => rel(dir, f));
  const has = (p) => existsSync(join(dir, p));
  const a = {
    root: dir,
    name: basename(dir),
    fileCount: files.length,
    languages: {},
    manifests: [],
    frameworks: new Set(),
    testFrameworks: new Set(),
    integrations: new Set(),
    scripts: {},
    sourceRoots: [],
    testRoots: [],
    testFiles: [],
    components: [],
    apiSpecs: [],
    dataFiles: [],
    infra: [],
    ci: [],
    docs: [],
    adrs: [],
    agentFiles: [],
    envExamples: [],
    toolingConfigs: [],
    existingAnnotations: 0,
    readmeTitle: null,
    readmeSummary: null,
    git: null,
    license: null,
  };

  for (const f of files) {
    const ext = extname(f).toLowerCase();
    if (LANGS[ext]) a.languages[LANGS[ext]] = (a.languages[LANGS[ext]] || 0) + 1;
    const b = basename(f);
    if (MANIFESTS[b] && !f.includes("/node_modules/")) a.manifests.push({ file: f, kind: MANIFESTS[b] });
    if (/(^|\/)(openapi|swagger)[^/]*\.(ya?ml|json)$/i.test(f) || ext === ".proto" || /\.graphqls?$/.test(f)) a.apiSpecs.push(f);
    if (/(^|\/)(migrations?|db\/migrate)\//i.test(f) || /schema\.prisma$|\.sql$/i.test(f)) a.dataFiles.push(f);
    if (/(^|\/)(Dockerfile|docker-compose[^/]*\.ya?ml)$|\.tf$|(^|\/)(k8s|helm|charts)\//i.test(f)) a.infra.push(f);
    if (/^\.github\/workflows\/|^\.gitlab-ci\.yml$|^Jenkinsfile$|^azure-pipelines\.yml$|^\.circleci\/|^bitbucket-pipelines\.yml$/.test(f)) a.ci.push(f);
    if (/^(README|CONTRIBUTING|CHANGELOG|SECURITY|CODEOWNERS)(\.md)?$/i.test(b) || /^docs?\//.test(f)) if (ext === ".md" || !ext) a.docs.push(f);
    if (/(^|\/)(adr|adrs|decisions)\/[^/]+\.md$/i.test(f)) a.adrs.push(f);
    if (/^(AGENTS\.md|CLAUDE\.md|GEMINI\.md|\.cursorrules|\.github\/copilot-instructions\.md|\.windsurfrules)$/.test(f) || f.startsWith(".claude/") || f.startsWith(".cursor/")) a.agentFiles.push(f);
    if (/(^|\/)\.env\.(example|sample|template)$/.test(f)) a.envExamples.push(f);
    if (!f.includes("/") && /^(tsconfig[^/]*\.json|\.eslintrc[^/]*|eslint\.config\.[a-z]+|\.prettierrc[^/]*|prettier\.config\.[a-z]+|biome\.jsonc?|\.stylelintrc[^/]*|jest\.config\.[a-z]+|\.markdownlint[^/]*)$/.test(f))
      a.toolingConfigs.push(f);
    if (/^LICEN[CS]E/i.test(b) && !f.includes("/")) a.license = f;
    if (!f.startsWith("docs/") && /(^|\/)(test|tests|__tests__|spec)\/|\.(test|spec)\.[a-z0-9]+$|_test\.(go|py)$|(^|\/)test_[^/]+\.py$/i.test(f)) a.testFiles.push(f);
  }

  // dependency based detection
  const depText = [];
  const pkgPath = join(dir, "package.json");
  if (existsSync(pkgPath)) {
    try {
      const pkg = JSON.parse(readFileSync(pkgPath, "utf8"));
      a.packageName = pkg.name;
      a.packageDescription = pkg.description;
      a.scripts = pkg.scripts || {};
      depText.push(...Object.keys({ ...(pkg.dependencies || {}), ...(pkg.devDependencies || {}), ...(pkg.peerDependencies || {}) }));
    } catch {
      /* unreadable package.json is reported, not fatal */
    }
  }
  for (const m of ["requirements.txt", "pyproject.toml", "go.mod", "Cargo.toml", "pom.xml", "build.gradle", "Gemfile", "composer.json"]) {
    const t = readText(join(dir, m));
    if (t) depText.push(t.toLowerCase());
  }
  const blob = depText.join("\n").toLowerCase();
  const hit = (k) => new RegExp(`(^|[^a-z0-9@-])${k.replace(/[.*+?^${}()|[\]\\/]/g, "\\$&")}([^a-z0-9-]|$)`, "m").test(blob);
  for (const [k, v] of FRAMEWORK_HINTS) if (hit(k)) a.frameworks.add(v);
  for (const [k, v] of TEST_HINTS) if (hit(k)) a.testFrameworks.add(v);
  for (const [k, v] of INTEGRATION_HINTS) if (blob.includes(k)) a.integrations.add(v);
  if (a.languages.Go && a.testFiles.some((f) => f.endsWith("_test.go"))) a.testFrameworks.add("go test");

  a.sourceRoots = SOURCE_ROOT_CANDIDATES.filter((d) => has(d) && files.some((f) => f.startsWith(d + "/") && LANGS[extname(f).toLowerCase()]));
  a.testRoots = TEST_ROOT_CANDIDATES.filter((d) => has(d));
  if (!a.sourceRoots.length) {
    const top = [...new Set(files.filter((f) => f.includes("/") && LANGS[extname(f).toLowerCase()]).map((f) => f.split("/")[0]))];
    const frameworkTools = existsSync(join(dir, "tools", "sdd", "cli.mjs"));
    a.sourceRoots = top.filter((d) => !TEST_ROOT_CANDIDATES.includes(d) && !d.startsWith(".") && d !== "docs" && !(frameworkTools && d === "tools")).slice(0, 5);
  }

  // components: the shallowest level under each source root with two or more domain folders
  const used = new Set();
  const isCode = (f) => !!LANGS[extname(f).toLowerCase()];
  const codeDirsUnder = (prefix) =>
    [...new Set(files.filter((f) => f.startsWith(prefix + "/") && isCode(f) && f.slice(prefix.length + 1).includes("/")).map((f) => f.slice(prefix.length + 1).split("/")[0]))]
      .filter((d) => !NON_DOMAIN_DIRS.has(d.toLowerCase()));
  const findDomains = (prefix, depth = 0) => {
    const subs = codeDirsUnder(prefix);
    if (depth < 4 && subs.length === 1) return findDomains(`${prefix}/${subs[0]}`, depth + 1);
    const wrapper = subs.find((d) => WRAPPER_DIRS.has(d.toLowerCase()) && codeDirsUnder(`${prefix}/${d}`).length >= 2);
    if (depth < 4 && wrapper && subs.length <= 3) return findDomains(`${prefix}/${wrapper}`, depth + 1);
    return subs.length >= 2 ? subs.map((d) => ({ name: d, path: `${prefix}/${d}` })) : [];
  };
  for (const root of a.sourceRoots) {
    const found = findDomains(root);
    const candidates = found.length ? found : [{ name: root === "src" ? a.name : root, path: root }];
    for (const c of candidates) {
      const name = c.name.toLowerCase().replace(/[^a-z0-9-]/g, "-").replace(/^-+|-+$/g, "") || "core";
      let prefix = name.replace(/[^a-z0-9]/g, "").toUpperCase().slice(0, 4) || "CORE";
      if (!/^[A-Z]/.test(prefix)) prefix = "C" + prefix.slice(0, 3);
      let n = 2;
      const base = prefix;
      while (used.has(prefix) || ["FR", "NFR", "OUT", "INV", "US", "AC", "ADR", "SPEC", "LLD", "PRD"].includes(prefix)) prefix = base.slice(0, 3) + n++;
      used.add(prefix);
      const compFiles = files.filter((f) => f.startsWith(c.path + "/") && isCode(f) && !a.testFiles.includes(f));
      const tests = a.testFiles.filter((f) => f.startsWith(c.path + "/") || new RegExp(`(^|/)${c.name}([./_-]|/)`, "i").test(f));
      a.components.push({ name, prefix, path: c.path, files: compFiles, tests, exports: extractExports(dir, compFiles.slice(0, 200)) });
    }
  }
  a.components = a.components.slice(0, 25);

  // existing annotations
  for (const f of files.filter((x) => LANGS[extname(x).toLowerCase()]).slice(0, 20000)) {
    const t = readText(join(dir, f));
    if (t && !isBinary(t)) a.existingAnnotations += (t.match(SPEC_ANNOTATION_RE) || []).length;
  }

  // README
  const readme = files.find((f) => /^readme\.md$/i.test(f));
  if (readme) {
    const t = readText(join(dir, readme)) || "";
    a.readmeTitle = (/^#\s+(.+)$/m.exec(t) || [])[1] || null;
    const para = t.split(/\n\s*\n/).map((p) => p.trim()).find((p) => p && !p.startsWith("#") && !p.startsWith("![") && !p.startsWith("[!") && !p.startsWith("<") && p.length > 40);
    a.readmeSummary = para ? para.replace(/\s+/g, " ").slice(0, 600) : null;
  }

  if (isGitRepo(dir)) {
    a.git = {
      branch: git(dir, ["rev-parse", "--abbrev-ref", "HEAD"]),
      commits: Number(git(dir, ["rev-list", "--count", "HEAD"]) || 0),
      lastCommit: git(dir, ["log", "-1", "--format=%cs"]),
      dirty: (git(dir, ["status", "--porcelain"]) || "").length > 0,
      remote: git(dir, ["remote", "get-url", "origin"]),
    };
  }
  a.frameworks = [...a.frameworks];
  a.testFrameworks = [...a.testFrameworks];
  a.integrations = [...a.integrations];
  return a;
}

function extractExports(dir, files) {
  const out = [];
  const res = [
    /export\s+(?:default\s+)?(?:async\s+)?(?:function|class|const|interface|type)\s+([A-Za-z0-9_]+)/g,
    /^def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(/gm,
    /^class\s+([A-Za-z_][A-Za-z0-9_]*)/gm,
    /^func\s+(?:\([^)]*\)\s*)?([A-Z][A-Za-z0-9_]*)\s*\(/gm,
    /\bpublic\s+(?:static\s+)?(?:class|interface|[A-Za-z<>[\]]+)\s+([A-Za-z0-9_]+)\s*[({]/g,
  ];
  for (const f of files) {
    const t = readText(join(dir, f));
    if (!t || isBinary(t)) continue;
    const names = new Set();
    for (const re of res) {
      re.lastIndex = 0;
      let m;
      while ((m = re.exec(t)) && names.size < 12) names.add(m[1]);
    }
    if (names.size) out.push({ file: f, names: [...names] });
  }
  return out;
}

// ---------------------------------------------------------------------------
// What the framework needs from people before it can run
// ---------------------------------------------------------------------------
export function missingInformation(a) {
  const yes = (cond, evidence) => (cond ? `Partly inferred: ${evidence}` : "Missing");
  const seed = [
    [1, "What problem are we solving, for whom, and why now?", "docs/prd/PRD-v1.md section 1.1, 1.2", yes(a.readmeSummary, "README summary (needs owner confirmation)")],
    [2, "What does success look like in numbers, and by when?", "PRD 1.4 Measurable outcomes", "Missing"],
    [3, "What are the top three things users must be able to do, in priority order?", "Component PRDs, user stories with P1 to P3", yes(a.components.length, `${a.components.length} component(s) found in code; stories are not inferable`)],
    [4, "What is explicitly out of scope?", "PRD 1.3 Scope and non-goals", "Missing"],
    [5, "What must never happen?", "PRD 1.7 Invariants", "Missing"],
    [6, "What are the latency, availability, scale and residency targets?", "PRD 2.5 Non-functional requirements", "Missing"],
    [7, "What data does it touch, and how is it classified?", "PRD 2.6 Data and classification", yes(a.dataFiles.length, `${a.dataFiles.length} schema or migration file(s); classification is not inferable`)],
    [8, "What systems must it integrate with or replace, and who owns them?", "PRD 2.7 Integrations and owners; SPEC", yes(a.integrations.length, a.integrations.join(", ") + " (owners and SLAs missing)")],
    [9, "What is already fixed (stack, vendors, platforms, budget)?", "AGENTS.md (repository instructions)", yes(Object.keys(a.languages).length, Object.keys(a.languages).join(", ") + (a.frameworks.length ? "; " + a.frameworks.join(", ") : "") + " (budget and vendor limits missing)")],
    [10, "Which decisions are already made, and which are open?", "docs/adr/", yes(a.adrs.length, `${a.adrs.length} existing ADR(s)`)],
    [11, "What is the rollout risk tolerance, and who responds when it fails?", "PRD 2.9 Rollout risk tolerance and support", yes(a.infra.length, "deployment files found; risk tolerance and on-call owner missing")],
    [12, "How will we know it is done?", "PRD 2.11 Definition of done", yes(a.testFiles.length, `${a.testFiles.length} existing test file(s); acceptance criteria missing`)],
  ];
  const framework = [
    ["Approvers for the intake checkpoint and Gates 1 to 3, the exception authority and the fast path criteria", "AGENTS.md, CODEOWNERS, approved_by in front matter", "Missing"],
    ["Organizational scope: the L1 domain, L2 capability and L3 Business Application this repository serves", "docs/scope/scope-map.yaml, project.scope in sdd.config.json", "Missing: the scope map has placeholders"],
    ["Who owns docs/ for review (CODEOWNERS) and whether branch protection requires that review", "Your repository settings (adopt never adds CODEOWNERS)", [".github/CODEOWNERS", "CODEOWNERS", "docs/CODEOWNERS"].some((f) => existsSync(join(a.root, f))) ? "Found a CODEOWNERS file: check that it covers docs/" : "Missing"],
    ["Confirm component names and requirement ID prefixes", "sdd.config.json components", a.components.length ? `Proposed: ${a.components.map((c) => `${c.name}=${c.prefix}`).join(", ")}` : "Missing: no components detected"],
    ["Test command", "AGENTS.md Commands", a.scripts.test ? `Inferred: npm test (${a.scripts.test})` : a.testFrameworks.length ? `Inferred framework: ${a.testFrameworks.join(", ")}; command missing` : "Missing"],
    ["Typecheck or lint command", "AGENTS.md Commands", a.scripts.typecheck || a.scripts.lint ? `Inferred: ${a.scripts.typecheck ? "npm run typecheck" : "npm run lint"}` : "Missing"],
    ["Build and run commands", "AGENTS.md Commands", a.scripts.build || a.scripts.start ? `Inferred: ${["build", "start", "dev"].filter((s) => a.scripts[s]).map((s) => "npm run " + s).join(", ")}` : "Missing"],
    ["CI system to run spec-lint and trace-check", ".github/workflows/sdd.yml or your CI", a.ci.length ? `Found: ${a.ci.slice(0, 3).join(", ")}` : "Missing: no CI detected"],
    ["Node.js 20 or later where the checks run", "Local machines and CI", "Check with: node tools/sdd/cli.mjs doctor"],
    ["Merge existing agent instructions with AGENTS.md", "AGENTS.md", a.agentFiles.length ? `Review .sdd-proposed/: ${a.agentFiles.slice(0, 5).join(", ")} already existed and were not changed` : "Not needed"],
    ["When the checks should start blocking merges", "CI: remove --advisory", "Missing: decide after the first components reach AUDITED"],
    ["Data classification scheme the organization uses", "PRD 2.6", "Missing"],
    [
      "Keep the framework's tools/ and .sdd-proposed/ out of the project's type check, lint, format and test tools",
      "The configs listed here (adopt never edits them)",
      a.toolingConfigs.length ? `Missing: check ${a.toolingConfigs.join(", ")}` : "Not needed: no type check, lint or format config found",
    ],
    ["Severity response targets (S0 to S4) and on-call owner", "PRD 2.9", "Missing"],
  ];
  return { seed, framework };
}

// ---------------------------------------------------------------------------
// Documents generated for an existing repository (all drafts; inferred content is tagged)
// ---------------------------------------------------------------------------
function inventoryDoc(a) {
  const L = [];
  const list = (items, empty = "None found") => (items.length ? items.slice(0, 40).map((x) => `- \`${x}\``).join("\n") + (items.length > 40 ? `\n- ... and ${items.length - 40} more` : "") : `- ${empty}`);
  L.push("---", `title: "Repository inventory"`, "type: inventory", "version: 1", "status: draft", `owner: "[Name]"`, `generated: ${today()}`, "---", "");
  L.push(`# Repository inventory (v1)`, "", `> **Owner:** A · **Persona:** \`analyst\` · Generated by \`sdd adopt\` on ${today()}. Everything here was read from the repository; nothing was run. Confirm or correct it, then use it to fill the H sections of the PRD.`, "");
  L.push("## Summary", "", "| Item | Found |", "| --- | --- |");
  L.push(`| Files scanned | ${a.fileCount} |`);
  L.push(`| Languages (files) | ${Object.entries(a.languages).sort((x, y) => y[1] - x[1]).map(([k, v]) => `${k} (${v})`).join(", ") || "none"} |`);
  L.push(`| Package managers | ${[...new Set(a.manifests.map((m) => m.kind))].join(", ") || "none"} |`);
  L.push(`| Frameworks | ${a.frameworks.join(", ") || "none detected"} |`);
  L.push(`| Test frameworks | ${a.testFrameworks.join(", ") || "none detected"} |`);
  L.push(`| Integrations | ${a.integrations.join(", ") || "none detected"} |`);
  L.push(`| Source roots | ${a.sourceRoots.join(", ") || "none detected"} |`);
  L.push(`| Test files | ${a.testFiles.length} |`);
  L.push(`| Existing @spec annotations | ${a.existingAnnotations} |`);
  L.push(`| Git | ${a.git ? `branch ${a.git.branch}, ${a.git.commits} commits, last ${a.git.lastCommit}${a.git.dirty ? ", uncommitted changes present" : ""}` : "not a git repository"} |`, "");
  L.push("## Components (proposed)", "", "| Component | Prefix | Path | Source files | Test files |", "| --- | --- | --- | --- | --- |");
  for (const c of a.components) L.push(`| ${c.name} | ${c.prefix} | \`${c.path}\` | ${c.files.length} | ${c.tests.length} |`);
  if (!a.components.length) L.push("| none detected | | | | |");
  L.push("", "## Package scripts", "", Object.keys(a.scripts).length ? Object.entries(a.scripts).map(([k, v]) => `- \`${k}\`: \`${v}\``).join("\n") : "- None found");
  L.push("", "## API specifications", "", list(a.apiSpecs));
  L.push("", "## Data schemas and migrations", "", list(a.dataFiles));
  L.push("", "## Infrastructure and deployment", "", list(a.infra));
  L.push("", "## CI configuration", "", list(a.ci));
  L.push("", "## Existing documentation", "", list(a.docs));
  L.push("", "## Existing decision records", "", list(a.adrs));
  L.push("", "## Existing agent instructions", "", list(a.agentFiles));
  L.push("", "## Environment examples", "", list(a.envExamples), "");
  return L.join("\n");
}

function missingDoc(a) {
  const m = missingInformation(a);
  const L = [];
  L.push("---", `title: "Information needed to start"`, "type: adoption-gaps", "version: 1", "status: draft", `owner: "[Name]"`, `generated: ${today()}`, "---", "");
  L.push("# Information needed to start using the SDD framework (v1)", "");
  L.push("> **Owner:** H · **Persona:** none (`analyst` may interview) · Generated by `sdd adopt`. Answer each missing item; the `sdd-intake` skill can interview the owner to capture the answers.", "");
  L.push("## The twelve seed questions", "", "| # | Question | Where the answer goes | Status |", "| --- | --- | --- | --- |");
  for (const [n, q, where, s] of m.seed) L.push(`| ${n} | ${q} | ${where} | ${s} |`);
  L.push("", "## Framework prerequisites", "", "| Item | Where it goes | Status |", "| --- | --- | --- |");
  for (const [q, where, s] of m.framework) L.push(`| ${q} | ${where} | ${s} |`);
  L.push("", "## Open questions", "");
  for (const [n, q, , s] of m.seed) if (!s.startsWith("Partly")) L.push(`- [ ] Q: (seed ${n}) ${q}`);
  for (const [q, , s] of m.framework) if (s.startsWith("Missing")) L.push(`- [ ] Q: ${q}`);
  L.push("");
  return L.join("\n");
}

function parentPrd(a) {
  const title = a.readmeTitle || a.packageName || a.name;
  const L = [];
  L.push("---", `title: "${title.replace(/"/g, "'")}"`, "type: prd", "version: 1", "status: draft", `owner: "[Name]"`, "---", "");
  L.push(`# ${title}: product requirements (v1)`, "");
  L.push("> Drafted by `sdd adopt` from the existing repository. Lines marked `[inferred]` were read from code or docs and need the owner's confirmation. Every H section must be written or confirmed by a person before Gate 1.", "");
  L.push("## 1.1 Problem and why now", "", "> **Owner:** H", "", a.readmeSummary ? `[inferred] ${a.readmeSummary}` : "- [ ] Q: What problem does this application solve, for whom, and why now?", "");
  L.push("## 1.2 Customers and users", "", "> **Owner:** H", "", "- [ ] Q: Who uses this application, and what do they need?", "");
  L.push("## 1.3 Scope and non-goals", "", "> **Owner:** H", "", "- [ ] Q: What is in scope and explicitly out of scope?", "");
  L.push("## 1.4 Measurable outcomes", "", "> **Owner:** H", "", "| ID | Metric | Baseline | Target | By when |", "| --- | --- | --- | --- | --- |", "", "- [ ] Q: What are two or three outcome metrics, with targets and dates?", "");
  L.push("## 1.7 Invariants: what must never happen", "", "> **Owner:** H", "", "| ID | The system must never | Source |", "| --- | --- | --- |", "", "- [ ] Q: What must this application never do?", "");
  L.push("## Components", "", "> **Owner:** C · **Persona:** `architect`", "", "| Component | Prefix | Component PRD |", "| --- | --- | --- |");
  for (const c of a.components) L.push(`| ${c.name} | ${c.prefix} | [PRD-${c.name}-v1](components/PRD-${c.name}-v1.md) |`);
  L.push("", "## Functional requirement index", "", "> **Owner:** H", "", "| ID | Requirement | Component |", "| --- | --- | --- |", "");
  L.push("## Non-functional requirements", "", "> **Owner:** H for targets", "", "| ID | Quality | Target | How it is measured |", "| --- | --- | --- | --- |", "", "- [ ] Q: What are the latency, availability, scale and residency targets?", "");
  return L.join("\n");
}

function componentPrd(a, c) {
  const L = [];
  L.push("---", `title: "${c.name}"`, "type: prd-component", "version: 1", "status: draft", `owner: "[Name]"`, `prefix: ${c.prefix}`, "parent: docs/prd/PRD-v1.md", "---", "");
  L.push(`# Component PRD: ${c.name} (v1)`, "");
  L.push(`> Drafted by \`sdd adopt\`. Requirement IDs for this component start with \`${c.prefix}-\`. Behavior that already exists in \`${c.path}\` should be captured as acceptance criteria and then cited from its tests with \`@spec\`.`, "");
  L.push("## What exists today", "", "> **Owner:** A · **Persona:** `analyst`", "", `[inferred] ${c.files.length} source file(s) in \`${c.path}\`, ${c.tests.length} related test file(s).`, "");
  for (const e of c.exports.slice(0, 15)) L.push(`- [inferred] \`${e.file}\`: ${e.names.join(", ")}`);
  L.push("", "## User stories and priority", "", "> **Owner:** C for stories (`product-writer`), H for priority", "", "| ID | As a... I want... so that... | Priority | Why this priority |", "| --- | --- | --- | --- |", "", "- [ ] Q: What are the top things users must be able to do with this component, in priority order?", "");
  L.push("## Acceptance criteria", "", "> **Owner:** C · **Persona:** `product-writer` drafts; the owner selects and approves", "", "| ID | Criterion | Requirement | Priority |", "| --- | --- | --- | --- |", "", "- [ ] Q: Which existing behaviors should become acceptance criteria first?", "");
  return L.join("\n");
}

function specDoc(a) {
  const L = [];
  L.push("---", `title: "System design"`, "type: spec", "version: 1", "status: draft", `owner: "[Name]"`, "parent: docs/prd/PRD-v1.md", "---", "");
  L.push("# SPEC: system high-level design (v1)", "", "> Drafted by `sdd adopt` from the current code. This describes the system as it is today; every `[inferred]` line needs the `architect` persona and the owner to confirm it before Gate 2.", "");
  L.push("## System context", "", "> **Owner:** C · **Persona:** `architect`", "", `[inferred] Languages: ${Object.keys(a.languages).join(", ") || "unknown"}. Frameworks: ${a.frameworks.join(", ") || "none detected"}.`, "");
  L.push("## Components", "", "> **Owner:** A · **Persona:** `architect`", "", "| Component | Path | Responsibility | LLD |", "| --- | --- | --- | --- |");
  for (const c of a.components) L.push(`| ${c.name} | \`${c.path}\` | [inferred] - [ ] Q: confirm | [LLD-${c.name}-v1](../lld/LLD-${c.name}-v1.md) |`);
  L.push("", "## Integrations and data stores", "", "> **Owner:** C · **Persona:** `architect`", "", a.integrations.length ? a.integrations.map((i) => `- [inferred] ${i}`).join("\n") : "- None detected", "");
  L.push("## Interfaces", "", "> **Owner:** A · **Persona:** `component-designer`", "", a.apiSpecs.length ? a.apiSpecs.map((f) => `- [inferred] \`${f}\``).join("\n") : "- No API specification files found", "");
  L.push("## Deployment", "", "> **Owner:** C · **Persona:** `sre`", "", a.infra.length ? a.infra.slice(0, 15).map((f) => `- [inferred] \`${f}\``).join("\n") : "- No deployment files found", "");
  L.push("## Open questions", "", "- [ ] Q: Which decisions in this design are settled, and which should become ADRs?", "");
  return L.join("\n");
}

function lldDoc(a, c) {
  const L = [];
  L.push("---", `title: "${c.name} low-level design"`, "type: lld", "version: 1", "status: draft", `owner: "[Name]"`, `prefix: ${c.prefix}`, "parent: docs/spec/SPEC-v1.md", "---", "");
  L.push(`# LLD: ${c.name} (v1)`, "", "> Drafted by `sdd adopt` from the current code. Rationale observed in code is tagged `[inferred]` until the owner confirms it.", "");
  L.push("## Module structure", "", "> **Owner:** A · **Persona:** `component-designer`", "", "| File | Exported names |", "| --- | --- |");
  for (const e of c.exports.slice(0, 40)) L.push(`| \`${e.file}\` | ${e.names.join(", ")} |`);
  if (!c.exports.length) L.push(`| \`${c.path}\` | none detected |`);
  L.push("", "## Tests that exist today", "", "> **Owner:** A · **Persona:** `test-architect`", "", c.tests.length ? c.tests.slice(0, 40).map((t) => `- \`${t}\``).join("\n") : "- None found", "");
  L.push("## Decisions and alternatives", "", "> **Owner:** A · **Persona:** `component-designer`", "", "| Decision | Rationale | Alternatives |", "| --- | --- | --- |", "| - [ ] Q: | [inferred] | |", "");
  return L.join("\n");
}

function traceIndex(a) {
  const comps = {};
  for (const c of a.components)
    comps[c.name] = { status: "MAPPED", scope: null, owner: null, sampled: today(), audited: null, audited_sha: null, findings: null, disposition: null, drift: null, next: "Write acceptance criteria for existing behavior, then annotate tests" };
  return "# Trace index: per-component audit state. Derived; maintained by the verifier and trace-check --write.\n" + toYaml({ schema_version: 2, components: comps });
}

export function planAdopt(target, a = analyzeRepo(target)) {
  const plan = new Plan(target);
  const keep = { onConflict: "keep" }; // generated documents: an existing file is the user's, leave it
  const vars = { PROJECT: a.packageName || a.name, DATE: today(), FRAMEWORK_VERSION, OWNER: "[Name]" };
  addMachinery(plan); // conflicting files become proposals
  plan.file("AGENTS.md", scaffoldText("AGENTS.md", vars));
  plan.file("CLAUDE.md", scaffoldText("CLAUDE.md", vars));
  plan.file(".claude/settings.json", scaffoldText("settings.json", vars));
  // an existing docs/README.md belongs to the application: the doc map goes beside it
  const docMap = existsSync(join(a.root, "docs", "README.md")) ? "docs/DOCMAP.md" : "docs/README.md";
  plan.file(docMap, scaffoldText("docs-README.md", vars), keep);
  plan.file("docs/glossary.md", scaffoldText("glossary.md", vars), keep);
  const testPlan = scaffoldText("test-plan-v1.md", vars);
  const testSection = "\n## Existing tests\n\n> **Owner:** A · **Persona:** `test-architect`\n\n" +
    (a.testFiles.length ? a.testFiles.slice(0, 60).map((t) => `- \`${t}\``).join("\n") : "- None found") + "\n";
  plan.file("docs/test/test-plan-v1.md", testPlan.replace(/\n## Deferrals and exceptions/, testSection + "\n## Deferrals and exceptions"), keep);
  plan.file("docs/scope/scope-map.yaml", scaffoldText("scope-map.yaml", vars), keep);
  plan.file("docs/adr/README.md", scaffoldText("adr-README.md", vars), keep);
  plan.file("docs/trace/index.yaml", traceIndex(a), keep);
  plan.file("docs/trace/coverage.md", scaffoldText("coverage.md", vars), keep);
  plan.file(
    "sdd.config.json",
    JSON.stringify(
      {
        $schema: "./tools/sdd/sdd.config.schema.json",
        frameworkVersion: FRAMEWORK_VERSION,
        project: { name: vars.PROJECT, description: a.packageDescription || "", scope: null },
        adoption: { mode: "advisory", adopted: today() },
        paths: {
          docs: "docs",
          codeRoots: a.sourceRoots.length ? a.sourceRoots : ["src"],
          testRoots: a.testRoots.length ? a.testRoots : ["test"],
          traceIndex: "docs/trace/index.yaml",
          coverage: "docs/trace/coverage.md",
          docMap,
          scopeMap: "docs/scope/scope-map.yaml",
        },
        approvals: { requireApprover: false },
        components: Object.fromEntries(a.components.map((c) => [c.name, { prefix: c.prefix, paths: [c.path] }])),
        trace: { staleAfterDays: 30, reachWarnBelow: 0.8 },
        features: { gateHook: true, protectApprovedDocs: true, reachReport: true, divergenceProbe: false, differentialAudit: false },
      },
      null,
      2,
    ) + "\n",
    keep,
  );
  plan.file("docs/adoption/inventory-v1.md", inventoryDoc(a), keep);
  plan.file("docs/adoption/missing-information-v1.md", missingDoc(a), keep);
  plan.file("docs/prd/PRD-v1.md", parentPrd(a), keep);
  for (const c of a.components) {
    plan.file(`docs/prd/components/PRD-${c.name}-v1.md`, componentPrd(a, c), keep);
    plan.file(`docs/lld/LLD-${c.name}-v1.md`, lldDoc(a, c), keep);
  }
  plan.file("docs/spec/SPEC-v1.md", specDoc(a), keep);
  const adrDir = join(a.root, "docs", "adr");
  const nums = existsSync(adrDir) ? readdirSync(adrDir).map((f) => Number(f.slice(0, 4))).filter((n) => !Number.isNaN(n)) : [];
  const already = existsSync(adrDir) && readdirSync(adrDir).some((f) => f.endsWith("-adopt-spec-driven-development.md"));
  if (!already) {
    const n = String((nums.length ? Math.max(...nums) : 0) + 1).padStart(4, "0");
    plan.file(`docs/adr/${n}-adopt-spec-driven-development.md`, scaffoldText("adr-adopt.md", { ...vars, NUMBER: n }), keep);
  }
  // CI: a separate advisory workflow; existing pipelines are never edited
  const usesGithub = a.ci.some((f) => f.startsWith(".github/")) || existsSync(join(a.root, ".github")) || /github\.com/.test(a.git?.remote || "");
  if (usesGithub) plan.file(".github/workflows/sdd.yml", scaffoldText("sdd-advisory.yml", vars), keep);
  for (const d of EMPTY_DIRS) plan.dir(d);
  return plan;
}

export function runAdopt(target, opts = {}, log = console.log) {
  const dir = resolve(target || ".");
  if (dir === FRAMEWORK_ROOT) {
    log("sdd adopt: run this against the application repository, not the framework repository itself.");
    return 1;
  }
  if (!existsSync(dir)) {
    log(`sdd adopt: ${dir} does not exist.`);
    return 1;
  }
  if (existsSync(join(dir, "sdd.config.json")) && !opts.force) {
    log(`sdd adopt: ${dir} already uses the framework (sdd.config.json exists). To bring in a newer release, run: sdd upgrade ${target || "."}`);
    return 1;
  }
  const a = analyzeRepo(dir);
  if (opts.json) {
    console.log(JSON.stringify({ analysis: { ...a, components: a.components.map(({ exports, files, tests, ...c }) => ({ ...c, files: files.length, tests: tests.length })) }, missing: missingInformation(a) }, null, 2));
    return 0;
  }
  log(`sdd adopt ${opts.apply ? "" : "(dry run: nothing will be written) "}-> ${dir}`);
  log(`  languages: ${Object.keys(a.languages).join(", ") || "none"}; components: ${a.components.map((c) => `${c.name} (${c.prefix})`).join(", ") || "none"}; tests: ${a.testFiles.length}`);
  if (a.git?.dirty && opts.apply && !opts["allow-dirty"]) {
    log("sdd adopt: the working tree has uncommitted changes. Commit or stash them first so the adoption is easy to review, or pass --allow-dirty.");
    return 1;
  }
  const plan = planAdopt(dir, a);
  plan.print(log);
  const m = missingInformation(a);
  const missingCount = m.seed.filter((s) => s[3] === "Missing").length + m.framework.filter((s) => s[2].startsWith("Missing")).length;
  log(`  information still needed from people: ${missingCount} item(s); see docs/adoption/missing-information-v1.md`);
  if (!opts.apply) {
    log("\nRe-run with --apply to write these files. Existing files are never changed.");
    return 0;
  }
  plan.apply();
  log("\nDone. Nothing existing was modified. Next steps:");
  log("  1. Review docs/adoption/missing-information-v1.md and answer the open questions (or run /sdd-adopt in Claude Code).");
  log("  2. Merge the files in .sdd-proposed/ into their originals by hand, then delete that folder.");
  log("  3. Run: node tools/sdd/cli.mjs doctor");
  log("  4. CI runs spec-lint and trace-check in advisory mode; remove --advisory once the first components are AUDITED.");
  return 0;
}
