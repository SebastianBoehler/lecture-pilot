import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const buildId = process.env.LECTUREPILOT_COMMIT_SHA?.trim() || "development";
const appVersion = JSON.parse(readFileSync(resolve(repoRoot, "package.json"), "utf8")).version;

export default defineConfig({
  define: {
    __LECTUREPILOT_APP_VERSION__: JSON.stringify(appVersion),
    __LECTUREPILOT_BUILD_ID__: JSON.stringify(buildId),
  },
  envDir: repoRoot,
  plugins: [
    react(),
    {
      name: "lecturepilot-version-manifest",
      generateBundle() {
        this.emitFile({
          type: "asset",
          fileName: "version.json",
          source: `${JSON.stringify({ buildId })}\n`,
        });
      },
    },
  ],
  test: {
    environment: "jsdom",
    setupFiles: "./src/test/setup.ts",
  },
});
