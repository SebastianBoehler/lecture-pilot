import { useI18n } from "./i18n";
import { ProfessorMaterialStep } from "./ProfessorMaterialStep";
import { ProfessorReviewStep } from "./ProfessorReviewStep";
import { ProfessorSourceRoutingStep } from "./ProfessorSourceRoutingStep";
import type { useProfessorCourseBuilder } from "./useProfessorCourseBuilder";

export function ProfessorBuilderMaterials({
  builder,
}: {
  builder: ReturnType<typeof useProfessorCourseBuilder>;
}) {
  const { t } = useI18n();
  const canRoute = builder.steps.find((step) => step.id === "sources")!.available;
  const canReviewMedia = builder.steps.find((step) => step.id === "review")!.available;
  return (
    <>
      {builder.activeStep === "upload" || !canRoute ? (
        <ProfessorMaterialStep {...builder.uploadStep} />
      ) : (
        <details className="builder-optional">
          <summary>{t("builder.materials.files")}</summary>
          <ProfessorMaterialStep {...builder.uploadStep} />
        </details>
      )}
      {canRoute ? <ProfessorSourceRoutingStep {...builder.routingStep} /> : null}
      {canReviewMedia ? (
        <details
          className="builder-optional"
          onToggle={(event) => {
            if (event.currentTarget.open) builder.setActiveStep("review");
            else if (builder.activeStep === "review") builder.setActiveStep("sources");
          }}
        >
          <summary>{t("builder.step.review")}</summary>
          <ProfessorReviewStep {...builder.mediaStep} />
        </details>
      ) : null}
    </>
  );
}
