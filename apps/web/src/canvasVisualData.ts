import { formatChartNumber } from "./canvasChartData";
import type {
  CanvasComponentData,
  CanvasComponentPoint,
  CanvasVisualAnnotation,
  CanvasVisualEdge,
  CanvasVisualNode,
  CanvasVisualSeries,
} from "./types";

export type ValidVisualData = CanvasComponentData & {
  visual_layout: "flow" | "timeline" | "grid" | "plot";
  visual_nodes: CanvasVisualNode[];
  visual_edges: CanvasVisualEdge[];
  visual_series: CanvasVisualSeries[];
  visual_annotations: CanvasVisualAnnotation[];
};

const NODE_ID = /^[a-zA-Z0-9][a-zA-Z0-9_-]*$/;

export function validVisualArtifact(
  data: CanvasComponentData | null | undefined,
): data is ValidVisualData {
  if (
    !data ||
    !["flow", "timeline", "grid", "plot"].includes(data.visual_layout ?? "") ||
    !Array.isArray(data.visual_nodes) ||
    !Array.isArray(data.visual_edges) ||
    !Array.isArray(data.visual_series) ||
    !Array.isArray(data.visual_annotations) ||
    data.visual_nodes.length > 12 ||
    data.visual_edges.length > 16 ||
    data.visual_series.length > 6 ||
    data.visual_annotations.length > 12
  ) {
    return false;
  }
  const visual = data as ValidVisualData;
  const nodeIds = new Set<string>();
  if (
    !visual.visual_nodes.every((node) => validNode(node, nodeIds)) ||
    !visual.visual_edges.every((edge) => validEdge(edge, nodeIds)) ||
    !visual.visual_annotations.every((annotation) => validAnnotation(annotation, nodeIds))
  ) {
    return false;
  }
  if (visual.visual_layout === "plot") return validPlot(visual);
  return (
    visual.visual_nodes.length >= 2 &&
    visual.visual_series.length === 0 &&
    (visual.visual_layout !== "grid" || visual.visual_edges.length === 0)
  );
}

export function visualPlotDescription(data: ValidVisualData) {
  const xLabel = data.x_label || "x";
  const yLabel = data.y_label || "y";
  return data.visual_series
    .map(
      (series) =>
        `${series.label} — ${series.points
          .map(
            (point) =>
              `${point.label}: ${xLabel} ${formatChartNumber(point.x)}, ${yLabel} ${formatChartNumber(point.y)}`,
          )
          .join("; ")}.`,
    )
    .join(" ");
}

export function visualPlotBounds(data: ValidVisualData) {
  const points = data.visual_series.flatMap((series) => series.points);
  const includeZero = data.visual_series.some((series) => series.mark === "bar");
  const xDomain = domain(
    points.map((point) => point.x),
    false,
  );
  const yDomain = domain(
    points.map((point) => point.y),
    includeZero,
  );
  return {
    x: paddedExtent(xDomain),
    y: paddedExtent(yDomain),
    xDomain,
    yDomain,
  } as const;
}

function validPlot(data: ValidVisualData) {
  return (
    text(data.x_label, 120) &&
    text(data.y_label, 120) &&
    data.visual_nodes.length === 0 &&
    data.visual_edges.length === 0 &&
    data.visual_series.length >= 1 &&
    data.visual_series.every(validSeries)
  );
}

function validNode(value: unknown, nodeIds: Set<string>): value is CanvasVisualNode {
  if (!isRecord(value)) return false;
  const id = value.id;
  if (!text(id, 80) || !NODE_ID.test(id) || nodeIds.has(id)) return false;
  nodeIds.add(id);
  return text(value.label, 120) && text(value.detail, 500) && nullableText(value.value, 80);
}

function validSeries(value: unknown): value is CanvasVisualSeries {
  if (!isRecord(value)) return false;
  return (
    text(value.label, 120) &&
    (value.mark === "line" || value.mark === "bar" || value.mark === "point") &&
    Array.isArray(value.points) &&
    value.points.length >= 2 &&
    value.points.length <= 24 &&
    value.points.every(validPoint)
  );
}

function validPoint(value: unknown): value is CanvasComponentPoint {
  if (!isRecord(value)) return false;
  return (
    text(value.label, 120) &&
    Number.isFinite(value.x) &&
    Number.isFinite(value.y) &&
    nullableText(value.series, 120)
  );
}

function validEdge(value: unknown, nodeIds: Set<string>): value is CanvasVisualEdge {
  if (!isRecord(value)) return false;
  return (
    text(value.from_id, 80) &&
    text(value.to_id, 80) &&
    value.from_id !== value.to_id &&
    nodeIds.has(value.from_id) &&
    nodeIds.has(value.to_id) &&
    nullableText(value.label, 120)
  );
}

function validAnnotation(value: unknown, nodeIds: Set<string>): value is CanvasVisualAnnotation {
  if (!isRecord(value)) return false;
  return (
    text(value.label, 300) &&
    (value.target_id == null || (text(value.target_id, 80) && nodeIds.has(value.target_id)))
  );
}

function text(value: unknown, maxLength: number): value is string {
  return typeof value === "string" && value.trim().length > 0 && value.length <= maxLength;
}

function nullableText(value: unknown, maxLength: number) {
  return value == null || text(value, maxLength);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function domain(values: number[], includeZero: boolean): [number, number] {
  const min = Math.min(...values, ...(includeZero ? [0] : []));
  const max = Math.max(...values, ...(includeZero ? [0] : []));
  return [min, max];
}

function paddedExtent([min, max]: [number, number]): [number, number] {
  const magnitude = Math.max(Math.abs(min), Math.abs(max), Number.MIN_VALUE);
  const normalizedMin = min / magnitude;
  const normalizedMax = max / magnitude;
  const span = normalizedMax - normalizedMin || Math.abs(normalizedMax) || 1;
  return [
    clampFinite((normalizedMin - span * 0.08) * magnitude),
    clampFinite((normalizedMax + span * 0.08) * magnitude),
  ];
}

function clampFinite(value: number) {
  return Math.max(-Number.MAX_VALUE, Math.min(Number.MAX_VALUE, value));
}
