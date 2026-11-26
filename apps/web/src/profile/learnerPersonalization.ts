export type LearnerPersonalizationUpdate = {
  background?: string;
  exampleInterests?: string;
  complete?: true;
};

export const PERSONALIZATION_LENGTH = 240;

export function personalizationFromPreferences(preferences: Record<string, unknown> = {}) {
  return {
    background: typeof preferences.background === "string" ? preferences.background : "",
    exampleInterests:
      typeof preferences.example_interests === "string" ? preferences.example_interests : "",
  };
}
