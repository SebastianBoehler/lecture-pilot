import { useI18n } from "./i18n";

export type BuilderStep = "define" | "upload" | "generate" | "review" | "publish";

type StepState = {
  available: boolean;
  id: BuilderStep;
  label: string;
  number: string;
  ready: boolean;
};

export function builderSteps({
  bundleReady,
  canvasReady,
  courseReady,
  draftReviewed,
  reviewAvailable,
  reviewReady,
  workspacePublished,
}: {
  bundleReady: boolean;
  canvasReady: boolean;
  courseReady: boolean;
  draftReviewed: boolean;
  reviewAvailable: boolean;
  reviewReady: boolean;
  workspacePublished: boolean;
}): StepState[] {
  return [
    { available: true, id: "define", label: "Define", number: "01", ready: courseReady },
    { available: courseReady, id: "upload", label: "Upload", number: "02", ready: bundleReady },
    { available: reviewAvailable, id: "review", label: "Media", number: "03", ready: reviewReady },
    { available: reviewReady || canvasReady, id: "generate", label: "Generate", number: "04", ready: canvasReady },
    {
      available: canvasReady && (draftReviewed || workspacePublished),
      id: "publish",
      label: "Publish",
      number: "05",
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
  if (bundleReady) return "review";
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
    <ol className="flow-stepper" aria-label={t("builder.progress")}>
      {steps.map((step) => (
        <li
          className={`${step.ready ? "is-ready" : ""} ${activeStep === step.id ? "is-active" : ""} ${
            step.available ? "" : "is-locked"
          }`}
          key={step.id}
        >
          <button
            aria-current={activeStep === step.id ? "step" : undefined}
            aria-label={`${step.number} ${builderStepLabel(step.id, t)}`}
            disabled={!step.available}
            type="button"
            onClick={() => onStepChange(step.id)}
          >
            <span>{step.number}</span>
            {builderStepLabel(step.id, t)}
          </button>
        </li>
      ))}
    </ol>
  );
}

function builderStepLabel(
  step: BuilderStep,
  t: (
    key:
      | "builder.step.define"
      | "builder.step.upload"
      | "builder.step.review"
      | "builder.step.generate"
      | "builder.step.publish",
  ) => string,
) {
  if (step === "define") return t("builder.step.define");
  if (step === "upload") return t("builder.step.upload");
  if (step === "review") return t("builder.step.review");
  if (step === "generate") return t("builder.step.generate");
  return t("builder.step.publish");
}
