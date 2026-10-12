import { useEffect, useState } from "react";

import { joinCourseInvite, previewCourseInvite, type CoursePreview } from "./courseInviteApi";
import { useI18n } from "./i18n";
import "./share-course.css";
import type { LoginSession } from "./types";

/** Landing for a shared course QR code or link; access stays Alma/ILIAS-based unless joinable. */
export function CourseLinkView({
  code,
  courseId,
  session,
  onOpenCourse,
  onSignIn,
}: {
  code?: string;
  courseId: string;
  session: LoginSession | null;
  onOpenCourse: (courseId: string) => void;
  onSignIn: (returnPath: string) => void;
}) {
  const { t } = useI18n();
  const joinPath = code
    ? `/join/${encodeURIComponent(courseId)}/${encodeURIComponent(code)}`
    : null;
  const [preview, setPreview] = useState<CoursePreview | null>(null);
  const [invalid, setInvalid] = useState(false);
  const [joining, setJoining] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const accessible = Boolean(session?.courses.some((course) => course.id === courseId));

  useEffect(() => {
    if (!joinPath) return;
    let cancelled = false;
    previewCourseInvite(joinPath)
      .then((loaded) => !cancelled && setPreview(loaded))
      .catch(() => !cancelled && setInvalid(true));
    return () => {
      cancelled = true;
    };
  }, [joinPath]);

  useEffect(() => {
    if (accessible) onOpenCourse(courseId);
  }, [accessible, courseId, onOpenCourse]);

  async function join() {
    if (!session || !joinPath) return;
    setJoining(true);
    setError(null);
    try {
      await joinCourseInvite(joinPath, session);
      // A fresh load refreshes the session's course list from the server.
      window.location.assign(`/courses/${encodeURIComponent(courseId)}`);
    } catch (joinError) {
      setError(joinError instanceof Error ? joinError.message : String(joinError));
      setJoining(false);
    }
  }

  return (
    <main className="course-link-screen">
      <section className="course-link-card" aria-labelledby="course-link-title">
        <h1 id="course-link-title">
          {preview
            ? t("courseLink.title", { course: preview.title })
            : t("courseLink.genericTitle")}
        </h1>
        {preview ? <p className="course-link-term">{preview.term}</p> : null}
        <p>{t("courseLink.intro")}</p>
        <ul>
          <li>{t("courseLink.point1")}</li>
          <li>{t("courseLink.point2")}</li>
          <li>{t("courseLink.point3")}</li>
        </ul>
        {invalid ? <p className="form-error">{t("courseLink.invalid")}</p> : null}
        {!session && !invalid ? (
          <button
            className="primary-action"
            type="button"
            onClick={() => onSignIn(joinPath ?? `/courses/${encodeURIComponent(courseId)}`)}
          >
            {t("courseLink.login")}
          </button>
        ) : null}
        {session && accessible ? <p role="status">{t("courseLink.loading")}</p> : null}
        {session && !accessible && joinPath && !invalid ? (
          <button
            className="primary-action"
            type="button"
            disabled={joining}
            onClick={() => void join()}
          >
            {joining ? t("courseLink.joining") : t("courseLink.join")}
          </button>
        ) : null}
        {session && !accessible && !joinPath ? (
          <p className="form-error">{t("courseLink.notEnrolled")}</p>
        ) : null}
        {error ? <p className="form-error">{error}</p> : null}
      </section>
    </main>
  );
}
