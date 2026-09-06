import { createContext } from "react";

export type CanvasAnnotation = {
  id: string;
  section_id: string;
  block_id: string;
  publication_version: number;
  quote: string;
  comment: string;
  created_at: string;
};

export const CanvasAnnotationContext = createContext<{
  annotations: CanvasAnnotation[];
  remove: (id: string) => Promise<void>;
} | null>(null);
