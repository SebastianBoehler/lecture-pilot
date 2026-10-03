import { createHash } from "node:crypto";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");
const manifest = JSON.parse(await readFile(resolve(root, "src/speech/whistleAssets.json"), "utf8"));
const directory = resolve(root, "public/speech", manifest.directory);
await mkdir(directory, { recursive: true });

for (const asset of manifest.files) {
  const destination = resolve(directory, asset.name);
  const suffix = Buffer.from(asset.append ?? "");
  try {
    const cached = await readFile(destination);
    const source = suffix.length ? cached.subarray(0, -suffix.length) : cached;
    if (digest(source) === asset.sha256 && cached.subarray(source.length).equals(suffix)) continue;
  } catch (cause) {
    if (cause.code !== "ENOENT") throw cause;
  }
  console.log(`Preparing Whistle: ${asset.name}`);
  const response = await fetch(asset.url, { signal: AbortSignal.timeout(120_000) });
  if (!response.ok) throw new Error(`Whistle ${asset.name}: HTTP ${response.status}`);
  const source = Buffer.from(await response.arrayBuffer());
  if (digest(source) !== asset.sha256) throw new Error(`Whistle ${asset.name}: checksum mismatch`);
  await writeFile(destination, Buffer.concat([source, suffix]));
}

function digest(bytes) {
  return createHash("sha256").update(bytes).digest("hex");
}
