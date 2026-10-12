import { describe, expect, it } from "vitest";

import { resolveApiBaseUrl } from "./apiBaseUrl";

describe("resolveApiBaseUrl", () => {
  it("always uses the same-origin proxy in production", () => {
    expect(resolveApiBaseUrl(true, "http://127.0.0.1:8000")).toBe("/api");
  });

  it("keeps the configured backend available during development", () => {
    expect(resolveApiBaseUrl(false, "http://localhost:9000")).toBe("http://localhost:9000");
    expect(resolveApiBaseUrl(false)).toBe("http://127.0.0.1:8000");
  });
});
