import { useMemo, useState } from "react";

import { useI18n } from "./i18n";
import { StepHeader } from "./ProfessorCourseBuilderParts";
import { ProfessorSourceRoutingEditor } from "./ProfessorSourceRoutingEditor";
import { lectureIdFromNumber } from "./professorWorkspaceActivation";
import {
  hasSupplementalBlindSpot,
  lectureRouteCounts,
  sourceRouteCounts,
} from "./sourceRoutingView";
import type { CourseSourceRoutingManifest, LectureScheduleItem, SourceRouteRole } from "./types";

export type SourceRoutingLectureOption = { id: string; label: string };

export function ProfessorSourceRoutingStep({
  isSaving,
  lectures,
  routing,
  onConfirm,
  onRegenerate,
  onRouteChange,
}: {
  isSaving: boolean;
  lectures: LectureScheduleItem[];
  routing: CourseSourceRoutingManifest | null;
  onConfirm: () => void;
  onRegenerate: () => void;
  onRouteChange: (path: string, role: SourceRouteRole, lectureId: string | null) => void;
}) {
  const { t } = useI18n();
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const lectureOptions = lectures.map((lecture) => ({
    id: lectureIdFromNumber(lecture.number),
    label: `${lecture.number} · ${lecture.title}`,
  }));
  const routes = useMemo(() => routing?.routes ?? [], [routing?.routes]);
  const counts = useMemo(() => sourceRouteCounts(routes), [routes]);
  const lectureCounts = useMemo(() => lectureRouteCounts(routes), [routes]);
  const coveredLectures = lectureOptions.filter(
    (lecture) => (lectureCounts.get(lecture.id) ?? 0) > 0,
  ).length;
  const supplementalBlindSpot = hasSupplementalBlindSpot(routes);

  return (
    <section className="flow-card">
      <StepHeader
        number="03"
        title={t("builder.sources.title")}
        done={Boolean(routing?.confirmed) && !supplementalBlindSpot}
      />
      <p className="flow-help">{t("builder.sources.help")}</p>
      <div className="source-routing-overview" role="list">
        <span role="listitem">
          {t("builder.sources.overviewAssigned", { count: counts.assigned })}
        </span>
        <span role="listitem">
          {t("builder.sources.overviewExcluded", { count: counts.excluded })}
        </span>
        <span role="listitem">
          {t("builder.sources.overviewCoverage", {
            covered: coveredLectures,
            total: lectureOptions.length,
          })}
        </span>
      </div>
      <div className="source-routing-primary-action">
        <button
          className="primary-action"
          disabled={
            !routes.length || Boolean(routing?.confirmed) || isSaving || supplementalBlindSpot
          }
          type="button"
          onClick={onConfirm}
        >
          {routing?.confirmed
            ? t("builder.sources.confirmed")
            : isSaving
              ? t("builder.sources.confirming")
              : t("builder.sources.confirm")}
        </button>
      </div>
      {supplementalBlindSpot ? (
        <div className="source-routing-warning" role="alert">
          <span>{t("builder.sources.supplementalWarning")}</span>
          <button disabled={isSaving} type="button" onClick={onRegenerate}>
            {isSaving ? t("builder.sources.rebuilding") : t("builder.sources.rebuild")}
          </button>
        </div>
      ) : null}
      <details className="source-routing-advanced" open={advancedOpen}>
        <summary
          onClick={(event) => {
            event.preventDefault();
            setAdvancedOpen((current) => !current);
          }}
        >
          <strong>{t("builder.sources.reviewOptional")}</strong>
          <span>{t("builder.sources.reviewOptionalHelp")}</span>
        </summary>
        {advancedOpen ? (
          <ProfessorSourceRoutingEditor
            lectureOptions={lectureOptions}
            routes={routes}
            onRouteChange={onRouteChange}
          />
        ) : null}
      </details>
    </section>
  );
}
