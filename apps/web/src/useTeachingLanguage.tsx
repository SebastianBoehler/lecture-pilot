import { useState } from "react";
import { languageRequest, type PublishedLanguages } from "./canvasLanguageApi";
import { teachingLanguageOverlay } from "./teachingLanguageOverlay";
import type { CanvasDocument, LoginSession } from "./types";

export function useTeachingLanguage(
  courseId: string,
  lectureId: string,
  session: LoginSession,
  document: CanvasDocument | null,
  version: number | null,
) {
  const [loaded, setLoaded] = useState<{ key: string; data: PublishedLanguages } | null>(null);
  const [selected, setSelected] = useState("canonical");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const key = `${session.tenant_id}:${session.username}:${courseId}:${lectureId}:${version}`;
  const data = loaded?.key === key ? loaded.data : null;
  const variant = data?.variants.find(
    (item) => item.language === selected && item.publication_version === version,
  );
  async function load() {
    setBusy(true);
    setError(null);
    try {
      setLoaded({
        key,
        data: await languageRequest<PublishedLanguages>(courseId, lectureId, session, "", false),
      });
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : "Teaching languages could not be loaded.",
      );
    } finally {
      setBusy(false);
    }
  }
  return {
    document:
      document && variant ? teachingLanguageOverlay(document, variant, data!.originals) : document,
    control: (
      <div className="teaching-language-control">
        {!data ? (
          <button type="button" disabled={busy} onClick={() => void load()}>
            {busy ? "Loading languages…" : "Teaching language"}
          </button>
        ) : (
          <label>
            Explanations{" "}
            <select
              value={variant ? selected : "canonical"}
              onChange={(event) => setSelected(event.target.value)}
            >
              <option value="canonical">Published course wording</option>
              {data.variants
                .filter((item) => item.publication_version === version)
                .map((item) => (
                  <option key={item.language} value={item.language}>
                    {item.language === "de" ? "Deutsch" : "English"}
                  </option>
                ))}
            </select>
          </label>
        )}
        {data ? (
          <span>
            Assessment language:{" "}
            {data.canonical_language === "de"
              ? "German"
              : data.canonical_language === "en"
                ? "English"
                : "not yet recorded by the professor"}
            . Published wording stays unchanged.
          </span>
        ) : null}
        {data?.unavailable_languages.length ? (
          <p role="status">
            Some teaching languages need professor review after a publication change.
          </p>
        ) : null}
        {error ? (
          <p className="form-error" role="alert">
            {error}
          </p>
        ) : null}
      </div>
    ),
  };
}
