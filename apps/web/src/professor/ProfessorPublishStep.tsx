import { useI18n } from "../i18n/i18n";
import { PendingStatus } from "./ProfessorCourseBuilderParts";

export function ProfessorPublishStep({
  canPublish,
  isFullCourse,
  isPublishing,
  onPublish,
  publishableCount = 0,
  publishedCount,
  ready,
  totalCount,
}: {
  canPublish: boolean;
  isFullCourse: boolean;
  isPublishing: boolean;
  onPublish: () => void;
  publishableCount?: number;
  publishedCount: number;
  ready: boolean;
  totalCount: number;
}) {
  const { t } = useI18n();
  const partial =
    isFullCourse && publishableCount > 0 && publishableCount < totalCount - publishedCount;
  const actionLabel = partial
    ? publishableCount === 1
      ? t("builder.publish.readyOne")
      : t("builder.publish.ready", { count: publishableCount })
    : isFullCourse
      ? t("builder.publish.all")
      : t("builder.publish.single");
  const busyLabel = isFullCourse ? t("builder.publish.busyAll") : t("builder.publish.busySingle");
  const statusLabel = isFullCourse
    ? t("builder.publish.statusAll", { count: totalCount })
    : t("builder.publish.statusSingle");
  return (
    <footer className="draft-review-footer">
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
    </footer>
  );
}
