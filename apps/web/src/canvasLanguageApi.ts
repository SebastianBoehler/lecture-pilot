import { apiUrl, readApiError } from "./api";
import { authRequestInit } from "./authz";
import type { LoginSession } from "./types";

export type TeachingText = { key: string; text: string };
export type LanguageVariant = {
  language: "de" | "en";
  digest: string;
  publication_version: number;
  texts: TeachingText[];
  published_at: string | null;
};
export type LanguagePreview = {
  draft: LanguageVariant | null;
  originals: TeachingText[];
  assessment_language: "de" | "en" | null;
  assessments: string[];
};
export type PublishedLanguages = {
  canonical_language: "de" | "en" | null;
  variants: LanguageVariant[];
  unavailable_languages: string[];
  originals: TeachingText[];
};

export async function languageRequest<T>(
  courseId: string,
  lectureId: string,
  session: LoginSession,
  suffix: string,
  admin: boolean,
  body?: object,
): Promise<T> {
  const response = await fetch(
    apiUrl(
      `${admin ? "/admin" : ""}/courses/${courseId}/lectures/${lectureId}/canvas/languages${suffix}`,
    ),
    authRequestInit(
      session,
      body
        ? {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
          }
        : {},
    ),
  );
  const payload: unknown = await response.json();
  if (!response.ok) throw new Error(readApiError(payload, "Teaching language request failed."));
  return payload as T;
}
