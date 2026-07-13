import { useI18n } from "./i18n";

export function CourseSyncSkeleton() {
  const { t } = useI18n();
  return (
    <div className="course-sync-skeleton" aria-busy="true" role="status">
      <span className="visually-hidden">{t("dashboard.loadingCourses")}</span>
      {[0, 1, 2, 3].map((index) => (
        <div aria-hidden="true" className="course-sync-skeleton-row" key={index}>
          <span className="course-sync-skeleton-title" />
          <span className="course-sync-skeleton-status" />
        </div>
      ))}
    </div>
  );
}

export function CourseSyncEmpty({ failed = false }: { failed?: boolean }) {
  const { t } = useI18n();
  return (
    <p className="workspace-empty" role={failed ? "alert" : undefined}>
      {t(failed ? "dashboard.courseSyncError" : "dashboard.noCourses")}
    </p>
  );
}
