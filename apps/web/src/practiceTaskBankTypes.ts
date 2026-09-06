import type { PracticeSourceAnchor } from "./practiceDesignTypes";

export type SupplementalPracticeTask = Readonly<{
  id: string;
  stage: "independent_exit" | "delayed_transfer";
  prompt: string;
  source_anchor: PracticeSourceAnchor;
  surface_change: string;
  numeric_assertions: readonly {
    operation: "add" | "subtract" | "multiply" | "divide";
    operands: readonly number[];
    expected: number;
    tolerance: number;
  }[];
}>;
