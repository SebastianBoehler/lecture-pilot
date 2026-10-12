import { describe, expect, it } from "vitest";

import { readApiError } from "./apiError";

describe("readApiError", () => {
  it("preserves structured coaching recovery instructions without exposing action paths", () => {
    expect(
      readApiError(
        {
          detail: {
            code: "coaching_state_recovery_required",
            message: "Persisted coaching state cannot be resumed safely. Recovery is required.",
            recovery_path: "/private/recovery-path",
          },
        },
        "Learner state loading failed.",
      ),
    ).toBe("Persisted coaching state cannot be resumed safely. Recovery is required.");
  });

  it.each([null, { detail: {} }, { detail: { message: " " } }, { detail: { message: 42 } }])(
    "keeps the explicit default for malformed details: %j",
    (payload) => expect(readApiError(payload, "Request failed.")).toBe("Request failed."),
  );

  it("preserves field validation and plain text errors", () => {
    expect(readApiError({ detail: [{ loc: ["body", "title"], msg: "Required" }] }, "Failed")).toBe(
      "title: Required",
    );
    expect(readApiError({ detail: " Access denied " }, "Failed")).toBe("Access denied");
  });
});
