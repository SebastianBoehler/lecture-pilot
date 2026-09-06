import { ProfessorLanguageVariants } from "./ProfessorLanguageVariants";
import type { LoginSession } from "./types";
import { useI18n } from "./i18n";
import { PendingStatus, StepHeader } from "./ProfessorCourseBuilderParts";

export function ProfessorPublishStep({
  courseId,
  session,
  canPublish,
  isFullCourse,
  isPublishing,
  lectures,
  onPublish,
  publishedCount,
  ready,
  totalCount,
}: {
  courseId?: string;
  session?: LoginSession;
  canPublish: boolean;
  isFullCourse: boolean;
  isPublishing: boolean;
  lectures: {
    id: string;
    label: string;
    previewHref: string;
    published: boolean;
  }[];
  onPublish: () => void;
  publishedCount: number;
  ready: boolean;
  totalCount: number;
}) {
  const { t } = useI18n();
  const actionLabel = isFullCourse ? t("builder.publish.all") : t("builder.publish.single");
  const busyLabel = isFullCourse ? t("builder.publish.busyAll") : t("builder.publish.busySingle");
  const statusLabel = isFullCourse
    ? t("builder.publish.statusAll", { count: totalCount })
    : t("builder.publish.statusSingle");
  return (
    <section className="flow-card wide">
      <StepHeader title={t("builder.publish.title")} done={ready} />
      {ready ? (
        <p className="drawer-note">{t("builder.publish.readyNote")}</p>
      ) : (
        <p className="drawer-note">{t("builder.publish.notReadyNote")}</p>
      )}
      {isFullCourse ? (
        <p>{t("builder.publish.progress", { published: publishedCount, total: totalCount })}</p>
      ) : null}
      {!ready ? (
        <button
          className="primary-action"
          disabled={!canPublish || isPublishing}
          type="button"
          onClick={onPublish}
        >
          {isPublishing ? busyLabel : actionLabel}
        </button>
      ) : null}
      {isPublishing ? <PendingStatus label={statusLabel} /> : null}
      {ready ? <PublishedLectureList lectures={lectures} /> : null}
      {ready && courseId && session
        ? lectures
            .filter((lecture) => lecture.published)
            .map((lecture) => (
              <section key={lecture.id}>
                <h3>{lecture.label}</h3>
                <ProfessorLanguageVariants
                  courseId={courseId}
                  lectureId={lecture.id}
                  session={session}
                />
              </section>
            ))
        : null}
    </section>
  );
}

function PublishedLectureList({
  lectures,
}: {
  lectures: {
    id: string;
    label: string;
    previewHref: string;
    published: boolean;
  }[];
}) {
  const { t } = useI18n();
  if (!lectures.length) return null;
  return (
    <div className="published-lecture-list" aria-label={t("builder.publish.list")}>
      <header>
        <strong>{t("builder.publish.list")}</strong>
        <span>{t("builder.publish.listHelp")}</span>
      </header>
      {lectures.map((lecture) => (
        <div className="published-lecture-row" key={lecture.id}>
          <span>{lecture.label}</span>
          <strong>
            {lecture.published ? t("builder.publish.published") : t("builder.publish.pending")}
          </strong>
          <a className="button-link" href={lecture.previewHref} rel="noreferrer" target="_blank">
            {t("builder.publish.preview")}
          </a>
        </div>
      ))}
    </div>
  );
}
