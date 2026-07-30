import type { CanvasComponentData, CanvasComponentFrame } from "./types";

export function validChartData(
  data: CanvasComponentData | null | undefined,
): data is CanvasComponentData {
  if (!data?.chart_type || data.frames.length === 0) return false;
  return data.frames.every((frame) => validFrame(data, frame));
}

export function formatChartNumber(value: number) {
  return Number.isInteger(value) ? String(value) : String(Number(value.toFixed(4)));
}

function validFrame(data: CanvasComponentData, frame: CanvasComponentFrame) {
  if (data.chart_type === "bar" || data.chart_type === "line") {
    return (
      data.labels.length >= 2 &&
      frame.values.length === data.labels.length &&
      frame.values.every(Number.isFinite)
    );
  }
  if (data.chart_type === "scatter") {
    return (
      Boolean(data.x_label && data.y_label) &&
      (frame.points?.length ?? 0) >= 2 &&
      (frame.points ?? []).every((point) => Number.isFinite(point.x) && Number.isFinite(point.y))
    );
  }
  const rowLabels = data.row_labels ?? [];
  return (
    data.labels.length >= 2 &&
    rowLabels.length >= 2 &&
    (frame.matrix?.length ?? 0) === rowLabels.length &&
    (frame.matrix ?? []).every(
      (row) => row.length === data.labels.length && row.every(Number.isFinite),
    )
  );
}
