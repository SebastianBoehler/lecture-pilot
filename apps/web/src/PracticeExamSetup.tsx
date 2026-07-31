import { useState } from "react";

import { useI18n } from "./i18n";
import { PpiExamSourcePicker } from "./PpiExamSourcePicker";
import {
  DEFAULT_PRACTICE_EXAM_QUESTIONS,
  MAX_PRACTICE_EXAM_QUESTIONS,
  MIN_PRACTICE_EXAM_QUESTIONS,
} from "./practiceExamLimits";
import type { PpiExamSource, PracticeExamGenerationInput } from "./practiceExamTypes";
import type { LoginSession, UniversityCourse } from "./types";
import { useModalDialog } from "./useModalDialog";

export function PracticeExamSetup({
  course,
  error,
  generating,
  session,
  sources,
  onClose,
  onGenerate,
  onSourceImported,
}: {
  course: UniversityCourse;
  error: string | null;
  generating: boolean;
  session: LoginSession;
  sources: PpiExamSource[];
  onClose: () => void;
  onGenerate: (input: PracticeExamGenerationInput) => void;
  onSourceImported: (source: PpiExamSource) => void;
}) {
  const { t } = useI18n();
  const [questionCount, setQuestionCount] = useState(DEFAULT_PRACTICE_EXAM_QUESTIONS);
  const [duration, setDuration] = useState(90);
  const [selectedSource, setSelectedSource] = useState<PpiExamSource | null>(
    sources.length === 1 ? sources[0] : null,
  );
  const [importingSource, setImportingSource] = useState(false);
  const dialogRef = useModalDialog();

  return (
    <dialog
      aria-labelledby="practice-exam-setup-title"
      aria-modal="true"
      className="practice-exam-dialog"
      ref={dialogRef}
      onCancel={(event) => {
        event.preventDefault();
        if (!importingSource) onClose();
      }}
    >
      <header>
        <div className="practice-exam-dialog-heading">
          <h2 id="practice-exam-setup-title">{t("practice.setup.title")}</h2>
          <p className="practice-exam-course">
            {t("practice.setup.course", { course: course.title })}
          </p>
        </div>
        <button
          aria-label={t("practice.setup.close")}
          className="practice-exam-dialog-close"
          disabled={importingSource}
          type="button"
          onClick={onClose}
        >
          <svg aria-hidden="true" viewBox="0 0 24 24">
            <path d="m6 6 12 12M18 6 6 18" />
          </svg>
        </button>
      </header>
      <div className="practice-exam-dialog-body">
        {error ? (
          <p className="practice-exam-error" role="alert">
            {error}
          </p>
        ) : null}
        <div className="practice-exam-settings">
          <label>
            <span>{t("practice.setup.questions")}</span>
            <input
              max={MAX_PRACTICE_EXAM_QUESTIONS}
              min={MIN_PRACTICE_EXAM_QUESTIONS}
              type="number"
              value={questionCount}
              onChange={(event) => setQuestionCount(Number(event.currentTarget.value))}
            />
          </label>
          <label>
            <span>{t("practice.setup.duration")}</span>
            <input
              max={300}
              min={30}
              type="number"
              value={duration}
              onChange={(event) => setDuration(Number(event.currentTarget.value))}
            />
          </label>
        </div>
        <p className="practice-exam-scope-help">{t("practice.setup.help")}</p>
        <section aria-labelledby="saved-ppi-sources">
          <div className="practice-exam-section-heading">
            <h3 id="saved-ppi-sources">{t("practice.ppi.saved")}</h3>
            <span>{t("practice.ppi.savedHelp")}</span>
          </div>
          {selectedSource ? (
            <div className="practice-ppi-ready" role="status">
              <div>
                <strong>{t("practice.ppi.ready")}</strong>
                <span>
                  {selectedSource.title} ·{" "}
                  {t("practice.ppi.protocolCount", { count: selectedSource.protocol_count })}
                </span>
              </div>
              <button
                disabled={generating || importingSource}
                type="button"
                onClick={() => setSelectedSource(null)}
              >
                {t("practice.ppi.changeSource")}
              </button>
            </div>
          ) : (
            <>
              {sources.length ? (
                <div aria-label={t("practice.ppi.chooseSource")} className="practice-source-list">
                  {sources.map((source) => (
                    <button key={source.id} type="button" onClick={() => setSelectedSource(source)}>
                      <span>{source.title}</span>
                      <span>
                        {t("practice.ppi.protocolCount", { count: source.protocol_count })}
                      </span>
                    </button>
                  ))}
                </div>
              ) : (
                <p className="practice-empty-copy">{t("practice.ppi.noneSaved")}</p>
              )}
              <PpiExamSourcePicker
                courseId={course.id}
                session={session}
                onImported={(source) => {
                  onSourceImported(source);
                  setSelectedSource(source);
                }}
                onImportingChange={setImportingSource}
              />
            </>
          )}
        </section>
      </div>
      <footer>
        <button disabled={importingSource} type="button" onClick={onClose}>
          {t("practice.cancel")}
        </button>
        <button
          className="practice-primary"
          disabled={
            generating ||
            importingSource ||
            questionCount < MIN_PRACTICE_EXAM_QUESTIONS ||
            questionCount > MAX_PRACTICE_EXAM_QUESTIONS
          }
          type="button"
          onClick={() =>
            onGenerate({
              question_count: questionCount,
              duration_minutes: duration,
              ppi_source_ids: selectedSource ? [selectedSource.id] : [],
            })
          }
        >
          {importingSource ? (
            <>
              <span aria-hidden="true" className="practice-button-spinner" />
              {t("practice.ppi.importingSource")}
            </>
          ) : generating ? (
            t("practice.generating")
          ) : (
            t("practice.generateCount", { count: questionCount })
          )}
        </button>
      </footer>
    </dialog>
  );
}
