#!/usr/bin/env node
/*
 * Fails if forbidden packages are introduced as dependencies or imported in code.
 */

const fs = require("node:fs");
const path = require("node:path");

const ROOT = path.resolve(__dirname, "..");
const FORBIDDEN_PACKAGES = ["axios", "crypto-js", "plain-crypto-js"];

const SKIP_DIRS = new Set([
  ".git",
  "node_modules",
  "dist",
  "dist-ssr",
  "build",
  ".venv",
  "venv",
  "__pycache__",
  ".pytest_cache",
  ".pytest_cache_local",
  ".mypy_cache",
  ".ruff_cache",
  ".tmp",
]);

const CODE_EXTENSIONS = new Set([
  ".js",
  ".jsx",
  ".mjs",
  ".cjs",
  ".json",
  ".py",
  ".sh",
  ".ps1",
  ".yml",
  ".yaml",
]);

function escapeForRegex(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function buildSourcePatterns() {
  const patterns = [];
  for (const pkg of FORBIDDEN_PACKAGES) {
    const escaped = escapeForRegex(pkg);
    const importTarget = `${escaped}(?:\\/[^"'\\s]+)?`;
    patterns.push(
      new RegExp(`\\bimport\\s+[^;\\n]*\\s+from\\s+["']${importTarget}["']`, "i"),
      new RegExp(`\\bimport\\s+["']${importTarget}["']`, "i"),
      new RegExp(`\\brequire\\(\\s*["']${importTarget}["']\\s*\\)`, "i"),
      new RegExp(`\\bimport\\(\\s*["']${importTarget}["']\\s*\\)`, "i")
    );
  }
  return patterns;
}

const SOURCE_PATTERNS = buildSourcePatterns();

function readText(filePath) {
  try {
    return fs.readFileSync(filePath, "utf8");
  } catch {
    return "";
  }
}

function listFiles(dirPath) {
  const results = [];
  let entries = [];
  try {
    entries = fs.readdirSync(dirPath, { withFileTypes: true });
  } catch {
    return results;
  }

  for (const entry of entries) {
    if (SKIP_DIRS.has(entry.name)) {
      continue;
    }

    const fullPath = path.join(dirPath, entry.name);
    if (entry.isDirectory()) {
      results.push(...listFiles(fullPath));
      continue;
    }

    if (!entry.isFile()) {
      continue;
    }

    if (CODE_EXTENSIONS.has(path.extname(entry.name).toLowerCase())) {
      results.push(fullPath);
    }
  }

  return results;
}

function findInPackageJson(issues) {
  const packageJsonPath = path.join(ROOT, "package.json");
  if (!fs.existsSync(packageJsonPath)) {
    return;
  }

  const raw = readText(packageJsonPath);
  if (!raw) {
    issues.push({
      file: "package.json",
      message: "Could not parse package.json.",
    });
    return;
  }

  let pkg;
  try {
    pkg = JSON.parse(raw);
  } catch {
    issues.push({
      file: "package.json",
      message: "Invalid JSON in package.json.",
    });
    return;
  }

  for (const depField of [
    "dependencies",
    "devDependencies",
    "optionalDependencies",
    "peerDependencies",
  ]) {
    for (const forbiddenPkg of FORBIDDEN_PACKAGES) {
      if (pkg[depField] && Object.prototype.hasOwnProperty.call(pkg[depField], forbiddenPkg)) {
        issues.push({
          file: "package.json",
          message: `Found ${forbiddenPkg} in ${depField}.`,
        });
      }
    }
  }
}

function findInPackageLock(issues) {
  const lockPath = path.join(ROOT, "package-lock.json");
  if (!fs.existsSync(lockPath)) {
    return;
  }

  const raw = readText(lockPath);
  if (!raw) {
    issues.push({
      file: "package-lock.json",
      message: "Could not parse package-lock.json.",
    });
    return;
  }

  let lock;
  try {
    lock = JSON.parse(raw);
  } catch {
    issues.push({
      file: "package-lock.json",
      message: "Invalid JSON in package-lock.json.",
    });
    return;
  }

  if (lock.packages && typeof lock.packages === "object") {
    for (const pkgPath of Object.keys(lock.packages)) {
      for (const forbiddenPkg of FORBIDDEN_PACKAGES) {
        const escaped = escapeForRegex(forbiddenPkg);
        const matcher = new RegExp(`(^|/)node_modules/${escaped}$`, "i");
        if (matcher.test(pkgPath)) {
          issues.push({
            file: "package-lock.json",
            message: `Found ${forbiddenPkg} lock entry: ${pkgPath}`,
          });
        }
      }
    }
  }

  if (lock.dependencies && typeof lock.dependencies === "object") {
    for (const forbiddenPkg of FORBIDDEN_PACKAGES) {
      if (Object.prototype.hasOwnProperty.call(lock.dependencies, forbiddenPkg)) {
        issues.push({
          file: "package-lock.json",
          message: `Found ${forbiddenPkg} in top-level lockfile dependencies.`,
        });
      }
    }
  }
}

function findInSourceFiles(issues) {
  const files = listFiles(ROOT);
  for (const filePath of files) {
    const relative = path.relative(ROOT, filePath).replace(/\\/g, "/");
    if (relative === "package.json" || relative === "package-lock.json") {
      continue;
    }

    const text = readText(filePath);
    if (!text) {
      continue;
    }

    const lines = text.split(/\r?\n/);
    for (let i = 0; i < lines.length; i += 1) {
      const line = lines[i];
      if (SOURCE_PATTERNS.some((pattern) => pattern.test(line))) {
        issues.push({
          file: relative,
          message: `Line ${i + 1}: ${line.trim()}`,
        });
      }
    }
  }
}

function main() {
  const issues = [];
  findInPackageJson(issues);
  findInPackageLock(issues);
  findInSourceFiles(issues);

  if (issues.length === 0) {
    console.log(`No forbidden package usage found (${FORBIDDEN_PACKAGES.join(", ")}).`);
    return 0;
  }

  console.error(
    `Forbidden package usage found (${FORBIDDEN_PACKAGES.join(", ")}). Issues found:`
  );
  for (const issue of issues) {
    console.error(`- ${issue.file}: ${issue.message}`);
  }
  return 1;
}

process.exit(main());
