import { useI18n } from "./i18n";
import { ProfessorMaterialStep } from "./ProfessorMaterialStep";
import { ProfessorSourceRoutingStep } from "./ProfessorSourceRoutingStep";
import type { useProfessorCourseBuilder } from "./useProfessorCourseBuilder";

export function ProfessorBuilderMaterials({
  builder,
}: {
  builder: ReturnType<typeof useProfessorCourseBuilder>;
}) {
  const { t } = useI18n();
  const canRoute = builder.steps.find((step) => step.id === "sources")!.available;
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
    </>
  );
}
