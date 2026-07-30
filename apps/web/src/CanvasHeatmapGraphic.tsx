import { formatChartNumber } from "./canvasChartData";
import type { CanvasComponentData, CanvasComponentFrame } from "./types";

type HeatmapGraphicProps = {
  ariaLabel: string;
  data: CanvasComponentData;
  frame: CanvasComponentFrame;
};

const WIDTH = 640;
const HEIGHT = 290;

export function HeatmapGraphic({ ariaLabel, data, frame }: HeatmapGraphicProps) {
  const rows = data.row_labels ?? [];
  const matrix = frame.matrix ?? [];
  const margin = { left: 130, right: 18, top: 58, bottom: 24 };
  const cellWidth = (WIDTH - margin.left - margin.right) / data.labels.length;
  const cellHeight = (HEIGHT - margin.top - margin.bottom) / rows.length;
  const values = matrix.flat();
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;

  return (
    <svg
      aria-label={ariaLabel}
      className="canvas-chart-graphic canvas-heatmap-graphic"
      role="img"
      viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
    >
      <text className="canvas-chart-axis-title" textAnchor="middle" x={WIDTH / 2} y="14">
        {data.x_label}
      </text>
      {data.labels.map((label, columnIndex) => (
        <text
          className="canvas-chart-label"
          key={label}
          textAnchor="middle"
          x={margin.left + cellWidth * (columnIndex + 0.5)}
          y={margin.top - 14}
        >
          {label}
        </text>
      ))}
      {rows.map((rowLabel, rowIndex) => (
        <g key={rowLabel}>
          <text
            className="canvas-chart-label"
            textAnchor="end"
            x={margin.left - 10}
            y={margin.top + cellHeight * (rowIndex + 0.55)}
          >
            {rowLabel}
          </text>
          {(matrix[rowIndex] ?? []).map((value, columnIndex) => {
            const intensity = (value - min) / range;
            return (
              <g key={`${rowLabel}-${data.labels[columnIndex]}`}>
                <rect
                  className="canvas-heatmap-cell"
                  fillOpacity={0.15 + intensity * 0.8}
                  height={Math.max(1, cellHeight - 4)}
                  width={Math.max(1, cellWidth - 4)}
                  x={margin.left + columnIndex * cellWidth + 2}
                  y={margin.top + rowIndex * cellHeight + 2}
                />
                <text
                  className={`canvas-heatmap-value${intensity > 0.55 ? " is-strong" : ""}`}
                  textAnchor="middle"
                  x={margin.left + cellWidth * (columnIndex + 0.5)}
                  y={margin.top + cellHeight * (rowIndex + 0.57)}
                >
                  {formatChartNumber(value)}
                </text>
              </g>
            );
          })}
        </g>
      ))}
      <text
        className="canvas-chart-axis-title"
        textAnchor="middle"
        transform={`rotate(-90 14 ${HEIGHT / 2})`}
        x="14"
        y={HEIGHT / 2}
      >
        {data.y_label}
      </text>
    </svg>
  );
}
