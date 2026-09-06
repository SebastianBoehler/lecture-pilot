import { useState } from "react";
import { languageRequest, type LanguagePreview, type LanguageVariant } from "./canvasLanguageApi";
import { MathText } from "./MathText";
import type { LoginSession } from "./types";

export function ProfessorLanguageVariants({
  courseId,
  lectureId,
  session,
}: {
  courseId: string;
  lectureId: string;
  session: LoginSession;
}) {
  const [assessmentLanguage, setAssessmentLanguage] = useState<"de" | "en" | "">("");
  const [language, setLanguage] = useState<"de" | "en">("de");
  const [preview, setPreview] = useState<LanguagePreview | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reviewed, setReviewed] = useState(false);
  async function run(action: "generate" | "preview" | "publish") {
    setBusy(true);
    setError(null);
    try {
      if (action === "generate")
        await languageRequest(courseId, lectureId, session, `/${language}/generate`, true, {});
      if (action === "publish") {
        if (!preview?.draft || !reviewed || !assessmentLanguage) return;
        const draft = await languageRequest<LanguageVariant>(
          courseId,
          lectureId,
          session,
          `/${language}/publish`,
          true,
          { digest: preview.draft.digest, assessment_language: assessmentLanguage },
        );
        setPreview({ ...preview, draft });
      } else {
        setPreview(
          await languageRequest<LanguagePreview>(
            courseId,
            lectureId,
            session,
            `/${language}`,
            true,
          ),
        );
        setReviewed(false);
        setAssessmentLanguage("");
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Language action failed.");
    } finally {
      setBusy(false);
    }
  }
  return (
    <details className="language-review">
      <summary>Reviewed teaching languages</summary>
      <p>
        Prepare shared explanations. Published assessment wording, formulas, code and source
        identities stay unchanged.
      </p>
      <label>
        Explanation language{" "}
        <select
          disabled={busy}
          value={language}
          onChange={(event) => {
            setLanguage(event.target.value as "de" | "en");
            setPreview(null);
            setReviewed(false);
          }}
        >
          <option value="de">Deutsch</option>
          <option value="en">English</option>
        </select>
      </label>
      <button type="button" disabled={busy} onClick={() => void run("generate")}>
        Generate language draft
      </button>
      <button type="button" disabled={busy} onClick={() => void run("preview")}>
        Review saved draft
      </button>
      {busy ? <p role="status">Preparing teaching language…</p> : null}
      {error ? (
        <p className="form-error" role="alert">
          {error}
        </p>
      ) : null}
      {preview && !preview.draft ? <p>No language draft has been generated.</p> : null}
      {preview?.draft ? (
        <>
          <details>
            <summary>Published assessment wording</summary>
            {preview.assessments.map((text, index) => (
              <MathText key={index} highlightedText={null} mode="block" text={text} />
            ))}
          </details>
          <label>
            Assessment language in the published wording
            <select
              value={assessmentLanguage}
              onChange={(event) => setAssessmentLanguage(event.target.value as "de" | "en")}
            >
              <option value="">Select after reviewing the wording</option>
              <option value="en">English</option>
              <option value="de">Deutsch</option>
            </select>
          </label>
          {preview.assessment_language ? (
            <p>
              Recorded for this publication:{" "}
              {preview.assessment_language === "de" ? "German" : "English"}.
            </p>
          ) : null}
          <div className="language-preview">
            {preview.draft.texts.map((text, index) => (
              <div key={text.key} className="language-comparison">
                <div>
                  <strong>Published wording</strong>
                  <MathText
                    highlightedText={null}
                    mode="block"
                    text={preview.originals[index]?.text ?? ""}
                  />
                </div>
                <div>
                  <strong>{language === "de" ? "Deutsch" : "English"}</strong>
                  <MathText highlightedText={null} mode="block" text={text.text} />
                </div>
              </div>
            ))}
          </div>
          {preview.draft.published_at ? (
            <p role="status">This reviewed teaching language is published.</p>
          ) : (
            <>
              <label>
                <input
                  type="checkbox"
                  checked={reviewed}
                  onChange={(event) => setReviewed(event.target.checked)}
                />{" "}
                I reviewed these explanations against the published teaching.
              </label>
              <button
                type="button"
                disabled={busy || !reviewed || !assessmentLanguage}
                onClick={() => void run("publish")}
              >
                Publish reviewed language
              </button>
            </>
          )}
        </>
      ) : null}
    </details>
  );
}
