import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const buildId = process.env.LECTUREPILOT_COMMIT_SHA?.trim() || "development";

export default defineConfig({
  define: {
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
