import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { expect, it } from "vitest";

const styles = readFileSync(resolve(process.cwd(), "src/styles.css"), "utf8");
const usageStyles = readFileSync(resolve(process.cwd(), "src/professor-usage.css"), "utf8");

it("loads usage responsive rules after the base usage stylesheet", () => {
  const baseImport = styles.indexOf('@import "./professor-usage.css";');
  const responsiveImport = styles.indexOf('@import "./professor-usage-responsive.css";');

  expect(baseImport).toBeGreaterThanOrEqual(0);
  expect(responsiveImport).toBeGreaterThan(baseImport);
  expect(usageStyles).not.toContain("professor-usage-responsive.css");
});
