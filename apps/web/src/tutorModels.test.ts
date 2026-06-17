import { describe, expect, it } from "vitest";

import { TUTOR_MODEL_OPTIONS } from "./tutorModels";

describe("tutor model options", () => {
  it("does not expose GLM design-assistant models in the tutor selector", () => {
    expect(TUTOR_MODEL_OPTIONS.map((option) => option.label).join(" ")).not.toMatch(/glm/i);
    expect(TUTOR_MODEL_OPTIONS.map((option) => option.value).join(" ")).not.toMatch(/glm/i);
  });
});
