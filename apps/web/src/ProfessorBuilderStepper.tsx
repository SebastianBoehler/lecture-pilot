export type BuilderStep = "define" | "upload" | "generate" | "review" | "publish";

type StepState = {
  id: BuilderStep;
  label: string;
  number: string;
  ready: boolean;
};

export function builderSteps({
  bundleReady,
  canvasReady,
  courseReady,
  videoReviewReady,
  workspacePublished,
}: {
  bundleReady: boolean;
  canvasReady: boolean;
  courseReady: boolean;
  videoReviewReady: boolean;
  workspacePublished: boolean;
}): StepState[] {
  return [
    { id: "define", label: "Define", number: "01", ready: courseReady },
    { id: "upload", label: "Upload", number: "02", ready: bundleReady },
    { id: "generate", label: "Generate", number: "03", ready: canvasReady },
    { id: "review", label: "Review", number: "04", ready: videoReviewReady },
    { id: "publish", label: "Publish", number: "05", ready: workspacePublished },
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
  if (canvasReady) return "review";
  if (bundleReady) return "generate";
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
  return (
    <ol className="flow-stepper" aria-label="Course builder progress">
      {steps.map((step) => (
        <li className={`${step.ready ? "is-ready" : ""} ${activeStep === step.id ? "is-active" : ""}`} key={step.id}>
          <button
            aria-current={activeStep === step.id ? "step" : undefined}
            aria-label={`${step.number} ${step.label}`}
            type="button"
            onClick={() => onStepChange(step.id)}
          >
            <span>{step.number}</span>
            {step.label}
          </button>
        </li>
      ))}
    </ol>
  );
}
