import { readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");
const sourcePath = resolve(root, "apps/web/src/productChangelog.json");
const markdownPath = resolve(root, "CHANGELOG.md");
const changelog = JSON.parse(readFileSync(sourcePath, "utf8"));
const [command = "check", versionArg, outputArg] = process.argv.slice(2);

validateSource();

if (command === "check") {
  validateCurrentVersion(versionArg);
  const expected = renderChangelog();
  const current = readFileSync(markdownPath, "utf8");
  if (current !== expected) fail("CHANGELOG.md is not synchronized with productChangelog.json.");
  console.log(`Changelog ${currentVersion()} is valid and synchronized.`);
} else if (command === "write") {
  writeFileSync(markdownPath, renderChangelog());
  console.log(`Wrote ${markdownPath}.`);
} else if (command === "release") {
  const version = normalizeVersion(versionArg);
  const release = changelog.releases.find((candidate) => candidate.version === version);
  if (!release) fail(`No changelog entry exists for ${versionArg}.`);
  const notes = renderReleaseNotes(release);
  if (outputArg) writeFileSync(resolve(root, outputArg), notes);
  else process.stdout.write(notes);
} else {
  fail(`Unknown command: ${command}`);
}

function validateSource() {
  if (!/^https:\/\/github\.com\/[\w.-]+\/[\w.-]+$/.test(changelog.repositoryUrl)) {
    fail("repositoryUrl must be a GitHub repository URL.");
  }
  if (!Array.isArray(changelog.releases) || changelog.releases.length === 0) {
    fail("At least one product release is required.");
  }
  const versions = new Set();
  let previousVersion = null;
  for (const release of changelog.releases) {
    if (!/^\d+\.\d+\.\d+$/.test(release.version)) fail(`Invalid version: ${release.version}`);
    if (versions.has(release.version)) fail(`Duplicate version: ${release.version}`);
    if (previousVersion && compareVersions(previousVersion, release.version) <= 0) {
      fail("Releases must be ordered newest first.");
    }
    if (!/^\d{4}-\d{2}-\d{2}$/.test(release.date)) fail(`Invalid date: ${release.date}`);
    validateLocalized(release.title, `${release.version} title`);
    validateLocalized(release.summary, `${release.version} summary`);
    if (!Array.isArray(release.changes) || release.changes.length === 0) {
      fail(`${release.version} needs at least one product change.`);
    }
    for (const change of release.changes) {
      validateLocalized(change.title, `${release.version} change title`);
      validateLocalized(change.description, `${release.version} change description`);
      if (change.feedbackDriven !== undefined && typeof change.feedbackDriven !== "boolean") {
        fail(`${release.version} feedbackDriven must be a boolean.`);
      }
    }
    versions.add(release.version);
    previousVersion = release.version;
  }
}

function validateLocalized(value, label) {
  if (!value || typeof value.en !== "string" || typeof value.de !== "string") {
    fail(`${label} must contain English and German text.`);
  }
  if (!value.en.trim() || !value.de.trim()) fail(`${label} cannot be empty.`);
}

function validateCurrentVersion(tag) {
  const expected = currentVersion();
  const versions = [
    ["package.json", readJsonVersion("package.json")],
    ["apps/web/package.json", readJsonVersion("apps/web/package.json")],
    ["apps/api/pyproject.toml", readPyprojectVersion()],
  ];
  for (const [file, version] of versions) {
    if (version !== expected) fail(`${file} is ${version}; expected ${expected}.`);
  }
  if (tag && normalizeVersion(tag) !== expected) {
    fail(`Tag ${tag} does not match current changelog version ${expected}.`);
  }
}

function currentVersion() {
  return changelog.releases[0].version;
}

function readJsonVersion(relativePath) {
  return JSON.parse(readFileSync(resolve(root, relativePath), "utf8")).version;
}

function readPyprojectVersion() {
  const source = readFileSync(resolve(root, "apps/api/pyproject.toml"), "utf8");
  const match = source.match(/^version = "([^"]+)"$/m);
  if (!match) fail("Could not read apps/api/pyproject.toml version.");
  return match[1];
}

function renderChangelog() {
  const lines = [
    "# LecturePilot changelog",
    "",
    "A product-level history of improvements for students and lecturers. Technical details remain in the commit history.",
    "",
    `[View all GitHub Releases](${changelog.repositoryUrl}/releases)`,
    "",
  ];
  for (const release of changelog.releases) {
    lines.push(...renderRelease(release, true), "");
  }
  return `${lines.join("\n").trim()}\n`;
}

function renderReleaseNotes(release) {
  return `${renderRelease(release, false).join("\n").trim()}\n`;
}

function renderRelease(release, includeVersionLink) {
  const version = includeVersionLink
    ? `[${release.version}](${changelog.repositoryUrl}/releases/tag/v${release.version})`
    : release.version;
  const lines = [
    `## ${version} — ${release.title.en}`,
    "",
    `Released ${release.date}`,
    "",
    release.summary.en,
    "",
    "### What changed",
    "",
    ...release.changes.map((change) => renderChange(change, "en")),
    "",
    "### Deutsch",
    "",
    `**${release.title.de}**`,
    "",
    release.summary.de,
    "",
    ...release.changes.map((change) => renderChange(change, "de")),
  ];
  return lines;
}

function renderChange(change, locale) {
  const feedback = change.feedbackDriven
    ? locale === "de"
      ? " _(Aus Feedback)_"
      : " _(From feedback)_"
    : "";
  return `- **${change.title[locale]}**${feedback} — ${change.description[locale]}`;
}

function normalizeVersion(version) {
  if (!version) fail("A release version or tag is required.");
  return version.startsWith("v") ? version.slice(1) : version;
}

function compareVersions(left, right) {
  const leftParts = left.split(".").map(Number);
  const rightParts = right.split(".").map(Number);
  for (let index = 0; index < 3; index += 1) {
    if (leftParts[index] !== rightParts[index]) return leftParts[index] - rightParts[index];
  }
  return 0;
}

function fail(message) {
  console.error(message);
  process.exit(1);
}
