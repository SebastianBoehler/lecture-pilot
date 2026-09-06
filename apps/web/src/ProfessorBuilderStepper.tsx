import { useI18n } from "./i18n";
import { builderStage, builderStages } from "./builderStages";

export type BuilderStep =
  "define" | "upload" | "sources" | "design" | "review" | "generate" | "publish";

export type StepState = {
  available: boolean;
  id: BuilderStep;
  ready: boolean;
};

export function builderSteps({
  bundleReady,
  canvasReady,
  courseReady,
  designAvailable = false,
  designReady,
  draftReviewed,
  reviewAvailable,
  reviewReady,
  routingReady,
  workspacePublished,
}: {
  bundleReady: boolean;
  canvasReady: boolean;
  courseReady: boolean;
  designAvailable?: boolean;
  designReady: boolean;
  draftReviewed: boolean;
  reviewAvailable: boolean;
  reviewReady: boolean;
  routingReady: boolean;
  workspacePublished: boolean;
}): StepState[] {
  return [
    { available: true, id: "define", ready: courseReady },
    { available: courseReady, id: "upload", ready: bundleReady },
    {
      available: reviewAvailable,
      id: "sources",
      ready: routingReady,
    },
    {
      available: routingReady || designAvailable,
      id: "design",
      ready: designReady,
    },
    { available: routingReady, id: "review", ready: reviewReady },
    {
      available: (routingReady && designReady) || canvasReady,
      id: "generate",
      ready: canvasReady,
    },
    {
      available: canvasReady && (draftReviewed || workspacePublished),
      id: "publish",
      ready: workspacePublished,
    },
  ];
}

export function initialBuilderStep({
  bundleReady,
  canvasReady,
  courseReady,
}: {
  bundleReady: boolean;
  canvasReady: boolean;
  courseReady: boolean;
}): BuilderStep {
  if (canvasReady) return "generate";
  if (bundleReady) return "sources";
  if (courseReady) return "upload";
  return "define";
}

export function ProfessorBuilderStepper({
  activeStep,
  steps,
  onStepChange,
}: {
  activeStep: BuilderStep;
  steps: StepState[];
  onStepChange: (step: BuilderStep) => void;
}) {
  const { t } = useI18n();
  return (
    <nav className="builder-journey" aria-label={t("builder.progress")}>
      <ol>
        {builderStages(steps).map((step, index) => (
          <li
            className={`${step.ready ? "is-ready" : ""} ${builderStage(activeStep) === step.id ? "is-active" : ""} ${
              step.available ? "" : "is-locked"
            }`}
            key={step.id}
          >
            <button
              aria-current={builderStage(activeStep) === step.id ? "step" : undefined}
              aria-label={`0${index + 1} ${t(`builder.journey.${step.id}`)}`}
              disabled={!step.available}
              type="button"
              onClick={() => onStepChange(step.target)}
            >
              <span>0{index + 1}</span>
              <strong>{t(`builder.journey.${step.id}`)}</strong>
            </button>
          </li>
        ))}
      </ol>
    </nav>
  );
}
