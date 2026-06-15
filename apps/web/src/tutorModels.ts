export type TutorModelId =
  | "gemini/gemini-3.1-flash-lite"
  | "openrouter/openai/gpt-oss-120b:nitro";

export type TutorModelPreference = "server-default" | TutorModelId;

export const TUTOR_MODEL_STORAGE_KEY = "lecturepilot.tutorModelPreference";

export const TUTOR_MODEL_OPTIONS: {
  value: TutorModelPreference;
  label: string;
  detail: string;
}[] = [
  {
    value: "server-default",
    label: "Server default",
    detail: "Uses the backend LECTUREPILOT_MODEL setting.",
  },
  {
    value: "gemini/gemini-3.1-flash-lite",
    label: "Gemini Flash Lite",
    detail: "Balanced default tutor model.",
  },
  {
    value: "openrouter/openai/gpt-oss-120b:nitro",
    label: "OpenRouter GPT-OSS 120B Nitro",
    detail: "Fast OpenRouter route for snappy tutor turns.",
  },
];

export function readStoredTutorModelPreference(): TutorModelPreference {
  const stored = window.localStorage.getItem(TUTOR_MODEL_STORAGE_KEY);
  return isTutorModelPreference(stored) ? stored : "server-default";
}

export function writeStoredTutorModelPreference(preference: TutorModelPreference) {
  window.localStorage.setItem(TUTOR_MODEL_STORAGE_KEY, preference);
}

export function requestedTutorModel(preference: TutorModelPreference): TutorModelId | null {
  return preference === "server-default" ? null : preference;
}

export function tutorModelLabel(preference: TutorModelPreference) {
  return TUTOR_MODEL_OPTIONS.find((option) => option.value === preference)?.label ?? "Server default";
}

function isTutorModelPreference(value: string | null): value is TutorModelPreference {
  return TUTOR_MODEL_OPTIONS.some((option) => option.value === value);
}
