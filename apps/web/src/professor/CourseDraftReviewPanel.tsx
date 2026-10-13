import { useEffect, useState } from "react";

import { useI18n } from "../i18n/i18n";
import { getPublishedCanvasView } from "../lesson/publishedCanvasView";
import { getDraftLectureCanvas } from "../shared/api";
import { errorMessage } from "../shared/errorMessage";
import type { LoginSession } from "../shared/types";
import { lessonPath } from "../shell/appRoute";
import { diffCanvasSections, type SectionDiff } from "./canvasSectionDiff";
import { CanvasSectionDiffView } from "./CanvasSectionDiffView";
import type { LectureState } from "./courseLectureStateTypes";
import type { LecturePending } from "./useCourseLectureActions";

/** Published canvas against the ready draft, with the single Approve & publish decision. */
export function CourseDraftReviewPanel({
  courseId,
  lecture,
  session,
  pending,
  onPublish,
}: {
  courseId: string;
  lecture: LectureState;
  session: LoginSession;
  pending?: LecturePending;
  onPublish: () => void;
}) {
  const { t } = useI18n();
  const lectureId = lecture.lecture_id;
  const published = lecture.published;
  const [diff, setDiff] = useState<SectionDiff[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    Promise.all([
      getDraftLectureCanvas(courseId, lectureId, session),
      published
        ? getPublishedCanvasView(courseId, lectureId, session, "professor-preview").then(
            (view) => view.document,
          )
        : Promise.resolve(null),
    ]).then(
      ([draft, current]) => active && setDiff(diffCanvasSections(current, draft)),
      (cause: unknown) => active && setError(errorMessage(cause, "The draft could not be loaded.")),
    );
    return () => {
      active = false;
    };
  }, [courseId, lectureId, published, session]);

  return (
    <section className="lecture-panel" aria-labelledby={`draft-${lectureId}`}>
      <h3 id={`draft-${lectureId}`}>{t("coursePage.draft.title")}</h3>
      <p className="lecture-panel-help">
        {published ? t("coursePage.draft.help") : t("coursePage.draft.firstVersion")}
      </p>
      {error ? <p role="alert">{error}</p> : null}
      {!diff && !error ? <p role="status">{t("coursePage.draft.loading")}</p> : null}
      {diff ? <CanvasSectionDiffView sections={diff} /> : null}
      <div className="lecture-panel-actions">
        <button
          className="course-row-button"
          data-primary
          type="button"
          disabled={Boolean(pending)}
          onClick={onPublish}
        >
          {pending === "publishing"
            ? t("coursePage.pending.publishing")
            : t("coursePage.draft.approve")}
        </button>
        <a
          className="course-quiet-button"
          href={lessonPath(courseId, lectureId, "draft")}
          target="_blank"
          rel="noopener"
        >
          {t("coursePage.draft.openPreview")}
        </a>
      </div>
    </section>
  );
}
