import { createContext } from "react";

export type CanvasPrediction = {
  block_id: string;
  section_id: string;
  publication_version: number;
  question: string;
  answer: string | null;
  created_at: string;
};

export const PredictionContext = createContext<{
  saved: CanvasPrediction[];
  loading: boolean;
  error: string | null;
  save: (blockId: string, answer: string | null) => Promise<void>;
} | null>(null);
