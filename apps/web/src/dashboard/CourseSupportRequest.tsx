import { Check } from "lucide-react";

import type { CourseSupportStatus } from "./courseSupportApi";
import { useI18n } from "../i18n/i18n";

export function CourseSupportRequest({
  courseTitle,
  failed,
  pending,
  status,
  onToggle,
}: {
  courseTitle: string;
  failed: boolean;
  pending: boolean;
  status: CourseSupportStatus;
  onToggle: (requested: boolean) => void;
}) {
  const { t } = useI18n();
  const others = status.request_count - (status.requested ? 1 : 0);
  return (
    <div className="course-support">
      {status.requested ? (
        <>
          <span className="course-support-requested">
            <Check aria-hidden="true" size={14} />
            {t("courseSupport.requested")}
          </span>
          <button
            aria-label={t("courseSupport.withdrawLabel", { course: courseTitle })}
            className="course-support-withdraw"
            disabled={pending}
            type="button"
            onClick={() => onToggle(false)}
          >
            {t("courseSupport.withdraw")}
          </button>
        </>
      ) : (
        <button
          aria-label={t("courseSupport.requestLabel", { course: courseTitle })}
          className="course-support-request"
          disabled={pending}
          type="button"
          onClick={() => onToggle(true)}
        >
          {t("courseSupport.request")}
        </button>
      )}
      <small className="course-support-count" aria-live="polite">
        {status.requested
          ? others === 0
            ? t("courseSupport.youAsked")
            : others === 1
              ? t("courseSupport.youAndOne")
              : t("courseSupport.youAndOthers", { count: others })
          : others === 1
            ? t("courseSupport.oneAsked")
            : others > 1
              ? t("courseSupport.manyAsked", { count: others })
              : null}
      </small>
      {failed ? (
        <small className="course-support-error" role="alert">
          {t("courseSupport.failed")}
        </small>
      ) : null}
    </div>
  );
}
