export type CanvasSectionId = string;
export type DocumentAnchorId = string;

export type CanvasComponentPoint = {
  label: string;
  x: number;
  y: number;
  series?: string | null;
};

export type CanvasComponentFrame = {
  label: string;
  values: number[];
  points?: CanvasComponentPoint[];
  matrix?: number[][];
  explanation: string;
};

export type CanvasComponentStep = {
  title: string;
  text: string;
};

export type CanvasComponentData = {
  chart_type: "bar" | "line" | "scatter" | "heatmap" | null;
  control_type?: "buttons" | "slider" | null;
  x_label: string | null;
  y_label: string | null;
  control_label: string | null;
  labels: string[];
  row_labels?: string[];
  frames: CanvasComponentFrame[];
  steps: CanvasComponentStep[];
};

export type CanvasBlock = {
  id: string;
  type:
    | "paragraph"
    | "list"
    | "asset"
    | "callout"
    | "math"
    | "video"
    | "checkpoint"
    | "quiz"
    | "table"
    | "component";
  text?: string | null;
  items: string[];
  asset_path?: string | null;
  asset_url?: string | null;
  caption?: string | null;
  answer_index?: number | null;
  component_id?: string | null;
  component_type?: string | null;
  component_ref?: string | null;
  component_version?: number | null;
  option_ids?: string[];
  component_data?: CanvasComponentData | null;
};

export type CanvasSection = {
  id: string;
  title: string;
  source_ref?: string | null;
  blocks: CanvasBlock[];
};

export type CanvasSectionPlacement = {
  mode: "after_section" | "before_section";
  section_id: string;
};

export type CanvasDocument = {
  id: string;
  import_version?: number;
  course_id: string;
  lecture_id: string;
  title: string;
  source_kind: "latex" | "markdown" | "generated";
  source_ref: string;
  workspace_path?: string;
  sections: CanvasSection[];
  warnings?: string[];
};

export type CanvasPublicationResult = {
  course_id: string;
  lecture_id: string;
  published: boolean;
  version?: number | null;
  published_at?: string | null;
};
