import { describe, expect, it } from "vitest";

import { readApiError } from "./api";

describe("readApiError", () => {
  it("reads a structured API error detail", () => {
    expect(
      readApiError(
        {
          code: "client_update_required",
          detail: "LecturePilot was updated. Reload this page to continue.",
        },
        "Request failed.",
      ),
    ).toBe("LecturePilot was updated. Reload this page to continue.");
  });

  it("turns FastAPI validation details into an actionable message", () => {
    expect(
      readApiError(
        {
          detail: [
            {
              type: "missing",
              loc: ["header", "Idempotency-Key"],
              msg: "Field required",
            },
          ],
        },
        "Request failed.",
      ),
    ).toBe("Idempotency-Key: Field required");
  });

  it("falls back for malformed API errors", () => {
    expect(readApiError({ detail: [{ loc: ["header"] }] }, "Request failed.")).toBe(
      "Request failed.",
    );
  });
});
