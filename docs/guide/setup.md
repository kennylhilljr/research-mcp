# Setting up a local environment

The framework needs only Node.js and git. Its tools have no dependencies, so they run the same way on macOS, Linux and Windows, in a container, or in CI.

## Requirements

| Tool | Version | Needed for |
| --- | --- | --- |
| Node.js | 20 or later | Every tool in `tools/` |
| git | Any recent version | Staleness and reach checks, commits |
| Claude Code | Latest | Running the skills, personas and hooks |
| Codex or another agent | Optional | Following the framework by hand through `AGENTS.md` |

The sample application in this repository also uses TypeScript and Vitest, installed by `npm install`. A repository set up with `sdd init` does not need them unless its own code does.

## Steps

1. **Install Node.js 20 or later.** Use the installer from nodejs.org or a version manager such as nvm, fnm or Volta. Check with `node --version`.
2. **Install git.** Check with `git --version`.
3. **Install Claude Code.** Follow the instructions at <https://code.claude.com>. Check with `claude --version`. The desktop and web apps work too.
4. **Clone this repository** and open a terminal in it.
5. **Run the setup:**

   ```bash
   npm run setup
   ```

   This installs the development dependencies and runs `node tools/sdd/cli.mjs doctor`, which checks Node, git, Claude Code, the configuration, the hooks, the skills and personas, and runs spec-lint and trace-check.

6. **Run the checks** at any time:

   ```bash
   npm test
   npm run typecheck
   node tools/sdd/cli.mjs check
   ```

## Using a dev container

`.devcontainer/devcontainer.json` defines a container with Node 20 and git. It installs the dependencies and Claude Code, then runs the doctor. Open the folder in VS Code with the Dev Containers extension, or in GitHub Codespaces, and choose "Reopen in Container".

## Platform notes

- **Windows.** Use PowerShell or Git Bash. The tools are plain Node scripts, so `node tools/sdd/cli.mjs ...` works in either. Paths in `sdd.config.json` always use forward slashes.
- **macOS and Linux.** No extra steps. `npm run setup` works in any shell.
- **CI.** `.github/workflows/ci.yml` runs on Ubuntu, Windows and macOS with Node 20 and 22. Other CI systems need only `node` and a checkout with history (`fetch-depth: 0`) for the reach check.

## Doctor output

| Status | Meaning |
| --- | --- |
| `ok` | The check passed |
| `warn` | Optional tool missing or advisory finding; the framework still works |
| `FAIL` | A required check failed; fix it before using the framework |
