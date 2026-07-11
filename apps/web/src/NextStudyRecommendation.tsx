import { useI18n } from "./i18n";
import type { Lecture } from "./types";

export function NextStudyRecommendation({
  lectures,
  passedLectureIds,
  onOpen,
}: {
  lectures: Lecture[];
  passedLectureIds: string[];
  onOpen: (lecture: Lecture) => void;
}) {
  const { t } = useI18n();
  const recommendation = recommendLecture(lectures, passedLectureIds);
  if (!recommendation) return null;

  return (
    <section className="next-study" aria-labelledby="next-study-heading">
      <div>
        <p className="section-label">{t("dashboard.recommendation.label")}</p>
        <h2 id="next-study-heading">{t("dashboard.recommendation.title")}</h2>
        <p>{reason(recommendation.reason, t)}</p>
      </div>
      <div className="next-study-action">
        <span>
          {t("dashboard.recommendation.lecture", { number: recommendation.lecture.number })}
        </span>
        <strong>{recommendation.lecture.title}</strong>
        <button type="button" onClick={() => onOpen(recommendation.lecture)}>
          {t("dashboard.recommendation.open", { number: recommendation.lecture.number })}
        </button>
      </div>
    </section>
  );
}

export function recommendLecture(lectures: Lecture[], passedLectureIds: string[]) {
  if (!lectures.length) return null;
  const passed = new Set(passedLectureIds);
  const incomplete = lectures.filter((lecture) => !passed.has(lecture.id));
  const missed = incomplete.find((lecture) => lecture.attendance === "absent");
  if (missed) return { lecture: missed, reason: "missed" as const };
  const diagnostic = incomplete.find((lecture) => lecture.attendance === "unknown");
  if (diagnostic) return { lecture: diagnostic, reason: "diagnostic" as const };
  if (incomplete[0]) return { lecture: incomplete[0], reason: "continue" as const };
  return { lecture: lectures.at(-1)!, reason: "review" as const };
}

function reason(
  kind: "missed" | "diagnostic" | "continue" | "review",
  t: ReturnType<typeof useI18n>["t"],
) {
  if (kind === "missed") return t("dashboard.recommendation.missed");
  if (kind === "diagnostic") return t("dashboard.recommendation.diagnostic");
  if (kind === "review") return t("dashboard.recommendation.review");
  return t("dashboard.recommendation.continue");
}
