import { afterEach, describe, expect, it } from "vitest";

import {
  readStoredTutorModelPreference,
  TUTOR_MODEL_OPTIONS,
  TUTOR_MODEL_STORAGE_KEY,
} from "./tutorModels";

describe("tutor model options", () => {
  afterEach(() => {
    window.localStorage.clear();
  });

  it("does not expose GLM design-assistant models in the tutor selector", () => {
    expect(TUTOR_MODEL_OPTIONS.map((option) => option.label).join(" ")).not.toMatch(/glm/i);
    expect(TUTOR_MODEL_OPTIONS.map((option) => option.value).join(" ")).not.toMatch(/glm/i);
  });

  it("falls back to the backend default for stale direct Gemini preferences", () => {
    window.localStorage.setItem(TUTOR_MODEL_STORAGE_KEY, "gemini/gemini-3.1-flash-lite");

    expect(readStoredTutorModelPreference()).toBe("server-default");
  });

  it("offers Gemini only through the stable OpenRouter route", () => {
    const values = TUTOR_MODEL_OPTIONS.map((option) => option.value);

    expect(values).not.toContain("gemini/gemini-3.1-flash-lite");
    expect(values).toContain("openrouter/google/gemini-3.1-flash-lite");
  });
});
