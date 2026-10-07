import { useEffect, useState } from "react";
import { languageRequest, type PublishedLanguages } from "./canvasLanguageApi";
import { useI18n } from "./i18n";
import { teachingLanguageOverlay } from "./teachingLanguageOverlay";
import type { CanvasDocument, LoginSession } from "./types";

export function useTeachingLanguage(
  courseId: string,
  lectureId: string,
  session: LoginSession,
  document: CanvasDocument | null,
  version: number | null,
  enabled = true,
) {
  const { t } = useI18n();
  const [loaded, setLoaded] = useState<{ key: string; data: PublishedLanguages } | null>(null);
  const [selected, setSelected] = useState("canonical");
  const key = `${session.tenant_id}:${session.username}:${courseId}:${lectureId}:${version}`;
  const data = loaded?.key === key ? loaded.data : null;
  const variants = data?.variants.filter((item) => item.publication_version === version) ?? [];
  const variant = variants.find((item) => item.language === selected);

  useEffect(() => {
    if (!enabled || version === null) return undefined;
    let cancelled = false;
    // Translations are optional: on failure learners keep the published wording.
    languageRequest<PublishedLanguages>(courseId, lectureId, session, "", false)
      .then((next) => {
        if (!cancelled && isPublishedLanguages(next)) setLoaded({ key, data: next });
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [courseId, enabled, key, lectureId, session, version]);

  const canonical = data?.canonical_language;
  const visible = enabled && variants.length > 0;
  return {
    document:
      document && variant ? teachingLanguageOverlay(document, variant, data!.originals) : document,
    control: visible ? (
      <div className="teaching-language-control">
        <label>
          <span>{t("teachingLanguage.label")}</span>
          <select
            value={variant ? selected : "canonical"}
            onChange={(event) => setSelected(event.target.value)}
          >
            <option value="canonical">{t("teachingLanguage.canonical")}</option>
            {variants.map((item) => (
              <option key={item.language} value={item.language}>
                {t(`language.${item.language}`)}
              </option>
            ))}
          </select>
        </label>
        {variant && canonical ? (
          <small>
            {t("teachingLanguage.assessmentNote", {
              language: t(`language.inline.${canonical}`),
            })}
          </small>
        ) : null}
        {data?.unavailable_languages.length ? (
          <small role="status">{t("teachingLanguage.pendingReview")}</small>
        ) : null}
      </div>
    ) : null,
  };
}

function isPublishedLanguages(value: unknown): value is PublishedLanguages {
  if (!value || typeof value !== "object") return false;
  const candidate = value as Partial<PublishedLanguages>;
  return (
    Array.isArray(candidate.variants) &&
    Array.isArray(candidate.unavailable_languages) &&
    Array.isArray(candidate.originals)
  );
}
