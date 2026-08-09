#!/usr/bin/env node
// Installs the skill into a project's agent skill directories.
//
// Copies rather than symlinks by default: symlinks need elevated privileges on
// Windows, and a copy is what most people want from a one-shot installer. Pass
// --link for the shared-copy layout instead.

import { cpSync, existsSync, mkdirSync, rmSync, symlinkSync, lstatSync } from "node:fs";
import { dirname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const NAME = "fft-battle-sprite";
const PAYLOAD = ["SKILL.md", "references", "scripts", "agents", "requirements.txt", "LICENSE"];
const TARGETS = { claude: ".claude/skills", codex: ".codex/skills" };

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const argv = process.argv.slice(2);

const has = (flag) => argv.includes(flag);
const valueOf = (flag, fallback) => {
  const i = argv.indexOf(flag);
  return i === -1 || i === argv.length - 1 ? fallback : argv[i + 1];
};

if (has("--help") || has("-h")) {
  console.log(`
Install the ${NAME} agent skill into the current project.

  npx github:jhihweijhan/${NAME} [options]

Options:
  --dir <path>   Project root to install into        (default: cwd)
  --claude       Install for Claude Code only
  --codex        Install for Codex CLI only
  --link         Keep one copy in .agents/skills and symlink both agents to it
  --force        Overwrite an existing installation
  -h, --help     Show this message

With no agent flag it installs for both.
`.trim());
  process.exit(0);
}

const projectRoot = resolve(valueOf("--dir", process.cwd()));
const wantClaude = has("--claude") || !has("--codex");
const wantCodex = has("--codex") || !has("--claude");
const force = has("--force");

if (!existsSync(projectRoot)) {
  console.error(`Not a directory: ${projectRoot}`);
  process.exit(1);
}

/** Refuse to clobber unless asked; a skill directory may hold local edits. */
function claim(dest) {
  if (!existsSync(dest)) return true;
  if (!force) {
    console.error(`Already installed: ${relative(projectRoot, dest) || dest}`);
    console.error("Pass --force to overwrite it.");
    return false;
  }
  rmSync(dest, { recursive: true, force: true });
  return true;
}

function copySkill(dest) {
  if (!claim(dest)) return false;
  mkdirSync(dest, { recursive: true });
  for (const entry of PAYLOAD) {
    const from = join(root, entry);
    if (existsSync(from)) cpSync(from, join(dest, entry), { recursive: true });
  }
  return true;
}

const installed = [];
let failed = false;

if (has("--link")) {
  const shared = join(projectRoot, ".agents/skills", NAME);
  if (!copySkill(shared)) process.exit(1);
  installed.push(shared);
  for (const [agent, dir] of Object.entries(TARGETS)) {
    if (agent === "claude" && !wantClaude) continue;
    if (agent === "codex" && !wantCodex) continue;
    const dest = join(projectRoot, dir, NAME);
    if (existsSync(dest) || isBrokenLink(dest)) {
      if (!force) {
        console.error(`Already present: ${relative(projectRoot, dest)} (use --force)`);
        failed = true;
        continue;
      }
      rmSync(dest, { recursive: true, force: true });
    }
    mkdirSync(dirname(dest), { recursive: true });
    symlinkSync(relative(dirname(dest), shared), dest, "junction");
    installed.push(dest);
  }
} else {
  for (const [agent, dir] of Object.entries(TARGETS)) {
    if (agent === "claude" && !wantClaude) continue;
    if (agent === "codex" && !wantCodex) continue;
    const dest = join(projectRoot, dir, NAME);
    if (copySkill(dest)) installed.push(dest);
    else failed = true;
  }
}

function isBrokenLink(p) {
  try {
    return lstatSync(p).isSymbolicLink();
  } catch {
    return false;
  }
}

if (installed.length === 0) process.exit(1);

console.log(`Installed ${NAME}:`);
for (const p of installed) console.log(`  ${relative(projectRoot, p) || p}`);
console.log(`
The downscaler needs Python 3.10+ with pillow and numpy:
  pip install -r ${relative(projectRoot, join(installed[0], "requirements.txt"))}

Image generation needs an agent with a built-in image tool. Codex CLI has one;
Claude Code does not, and can run the postprocessing half only.`);

process.exit(failed ? 1 : 0);
