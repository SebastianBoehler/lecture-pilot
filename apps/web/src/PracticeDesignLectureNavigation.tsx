import { useI18n } from "./i18n";
import { isApproved } from "./ProfessorPracticeDesignStep.helpers";
import type { PracticeDesign } from "./practiceDesignTypes";
import type { PendingEntry } from "./practiceDesignOperations";

export function PracticeDesignLectureNavigation({
  lectures,
  designs,
  selectedId,
  pendingByLecture,
  preparing,
  routingReady,
  errorsByLecture,
  onSelect,
}: {
  lectures: { id: string; label: string }[];
  designs: Readonly<Record<string, PracticeDesign>>;
  selectedId: string | undefined;
  pendingByLecture: Readonly<Record<string, PendingEntry>>;
  preparing: boolean;
  routingReady: boolean;
  errorsByLecture: Readonly<Record<string, string>>;
  onSelect: (id: string) => void;
}) {
  const { t } = useI18n();
  const approved = lectures.filter(
    ({ id }) => routingReady && designs[id] && isApproved(designs[id]),
  ).length;
  return (
    <nav className="practice-plan-navigation" aria-label={t("builder.plan.lectures")}>
      <p>{t("builder.generate.reviewProgress", { approved, total: lectures.length })}</p>
      {lectures.map((lecture) => {
        const design = designs[lecture.id];
        const pending = pendingByLecture[lecture.id];
        const label = !routingReady
          ? "stale"
          : errorsByLecture[lecture.id]
            ? "failed"
            : pending
              ? "working"
              : design
                ? isApproved(design)
                  ? "approved"
                  : "review"
                : preparing
                  ? "queued"
                  : "missing";
        return (
          <button
            key={lecture.id}
            type="button"
            aria-current={selectedId === lecture.id ? "true" : undefined}
            onClick={() => onSelect(lecture.id)}
          >
            <strong>{lecture.label}</strong>
            <span>{t(`builder.plan.${label}`)}</span>
          </button>
        );
      })}
    </nav>
  );
}
