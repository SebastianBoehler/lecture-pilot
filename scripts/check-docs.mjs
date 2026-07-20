import { execFileSync } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";

const repositoryRoot = process.cwd();
const markdownFiles = [
  ...gitFiles(["ls-files", "-z", "--", "*.md"]),
  ...gitFiles(["ls-files", "-z", "--others", "--exclude-standard", "--", "*.md"]),
];

const failures = [];

for (const file of markdownFiles) {
  const absoluteFile = resolve(repositoryRoot, file);
  const source = readFileSync(absoluteFile, "utf8");
  const targets = [
    ...matches(source, /!?\[[^\]]*\]\((<[^>]+>|[^\s)]+)(?:\s+['"][^)]*['"])?\)/g),
    ...matches(source, /\b(?:href|src)=["']([^"']+)["']/g),
  ];

  for (const target of targets) {
    const localPath = localTarget(target);
    if (!localPath) continue;
    const resolved = resolve(dirname(absoluteFile), localPath);
    if (!existsSync(resolved)) failures.push(`${file}: missing link target ${target}`);
  }
}

if (failures.length) {
  console.error(failures.join("\n"));
  process.exit(1);
}

console.log(`Checked local links in ${markdownFiles.length} tracked Markdown files.`);

function matches(source, pattern) {
  return [...source.matchAll(pattern)].map((match) => match[1]);
}

function gitFiles(args) {
  return execFileSync("git", args, { cwd: repositoryRoot, encoding: "utf8" })
    .split("\0")
    .filter(Boolean);
}

function localTarget(value) {
  const unwrapped = value.startsWith("<") && value.endsWith(">") ? value.slice(1, -1) : value;
  if (
    !unwrapped ||
    unwrapped.startsWith("#") ||
    unwrapped.startsWith("/") ||
    /^[a-z][a-z0-9+.-]*:/i.test(unwrapped)
  ) {
    return null;
  }
  const path = unwrapped.split(/[?#]/, 1)[0];
  try {
    return decodeURIComponent(path);
  } catch {
    return path;
  }
}
