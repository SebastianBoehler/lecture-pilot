import type { BuilderStep, StepState } from "./ProfessorBuilderStepper";

export type BuilderStage = "course" | "materials" | "plan" | "release";

export function builderStage(step: BuilderStep): BuilderStage {
  if (step === "define") return "course";
  if (step === "upload" || step === "sources" || step === "review") return "materials";
  return step === "design" ? "plan" : "release";
}

export function builderStages(steps: StepState[]) {
  const state = (id: BuilderStep) => steps.find((step) => step.id === id)!;
  return [
    { id: "course", target: "define", available: true, ready: state("define").ready },
    {
      id: "materials",
      target: state("sources").available ? "sources" : "upload",
      available: state("upload").available,
      ready: state("upload").ready && state("sources").ready,
    },
    {
      id: "plan",
      target: "design",
      available: state("design").available,
      ready: state("design").ready,
    },
    {
      id: "release",
      target: "generate",
      available: state("generate").available,
      ready: state("publish").ready,
    },
  ] satisfies { id: BuilderStage; target: BuilderStep; available: boolean; ready: boolean }[];
}
