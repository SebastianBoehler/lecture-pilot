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
  mediaReady,
  workspacePublished,
}: {
  bundleReady: boolean;
  canvasReady: boolean;
  courseReady: boolean;
  mediaReady: boolean;
  workspacePublished: boolean;
}): StepState[] {
  return [
    { id: "define", label: "Define", number: "01", ready: courseReady },
    { id: "upload", label: "Upload", number: "02", ready: bundleReady },
    { id: "review", label: "Media", number: "03", ready: mediaReady },
    { id: "generate", label: "Generate", number: "04", ready: canvasReady },
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
  if (canvasReady) return "publish";
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
