import { HeatmapGraphic } from "./CanvasHeatmapGraphic";
import type { CanvasComponentData, CanvasComponentFrame, CanvasComponentPoint } from "./types";
import { formatChartNumber } from "./canvasChartData";

type ChartGraphicProps = {
  ariaLabel: string;
  data: CanvasComponentData;
  frame: CanvasComponentFrame;
};

const WIDTH = 640;
const HEIGHT = 290;
const PLOT = { left: 62, right: 20, top: 28, bottom: 58 };

export function ChartGraphic({ ariaLabel, data, frame }: ChartGraphicProps) {
  if (data.chart_type === "heatmap") {
    return <HeatmapGraphic ariaLabel={ariaLabel} data={data} frame={frame} />;
  }
  return <CartesianGraphic ariaLabel={ariaLabel} data={data} frame={frame} />;
}

function CartesianGraphic({ ariaLabel, data, frame }: ChartGraphicProps) {
  const plotWidth = WIDTH - PLOT.left - PLOT.right;
  const plotHeight = HEIGHT - PLOT.top - PLOT.bottom;
  const scatter = data.chart_type === "scatter";
  const points = frame.points ?? [];
  const xValues = scatter ? points.map((point) => point.x) : data.labels.map((_, index) => index);
  const yValues = scatter ? points.map((point) => point.y) : frame.values;
  const [minX, maxX] = paddedExtent(xValues);
  const [minY, maxY] = scatter ? paddedExtent(yValues) : valueExtent(yValues);
  const x = (value: number) => PLOT.left + ((value - minX) / (maxX - minX)) * plotWidth;
  const y = (value: number) => PLOT.top + ((maxY - value) / (maxY - minY)) * plotHeight;
  const baseline = scatter ? HEIGHT - PLOT.bottom : y(0);

  return (
    <svg
      aria-label={ariaLabel}
      className="canvas-chart-graphic"
      role="img"
      viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
    >
      <line
        className="canvas-chart-axis"
        x1={PLOT.left}
        x2={WIDTH - PLOT.right}
        y1={baseline}
        y2={baseline}
      />
      <line
        className="canvas-chart-axis"
        x1={PLOT.left}
        x2={PLOT.left}
        y1={PLOT.top}
        y2={HEIGHT - PLOT.bottom}
      />
      {scatter ? (
        <ScatterMarks points={points} x={x} y={y} />
      ) : data.chart_type === "line" ? (
        <LineMarks data={data} frame={frame} x={x} y={y} />
      ) : (
        <BarMarks data={data} frame={frame} baseline={baseline} y={y} />
      )}
      {scatter ? null : <CategoryLabels data={data} />}
      {scatter ? (
        <ScatterAxes data={data} minX={minX} maxX={maxX} minY={minY} maxY={maxY} />
      ) : (
        <text className="canvas-chart-value-label" x={PLOT.left} y="16">
          {data.y_label}
        </text>
      )}
      {scatter ? <ScatterLegend points={points} /> : null}
    </svg>
  );
}

function ScatterMarks({
  points,
  x,
  y,
}: {
  points: CanvasComponentPoint[];
  x: (value: number) => number;
  y: (value: number) => number;
}) {
  const series = seriesNames(points);
  return points.map((point, index) => {
    const seriesIndex = Math.max(0, series.indexOf(point.series || ""));
    return (
      <circle
        className={`canvas-chart-point canvas-chart-series-${seriesIndex % 3}`}
        cx={x(point.x)}
        cy={y(point.y)}
        key={`${point.label}-${index}`}
        r="6"
      >
        <title>
          {point.label}: {formatChartNumber(point.x)}, {formatChartNumber(point.y)}
        </title>
      </circle>
    );
  });
}

function ScatterLegend({ points }: { points: CanvasComponentPoint[] }) {
  const series = seriesNames(points);
  if (series.length < 2) return null;
  return (
    <g className="canvas-chart-legend">
      {series.slice(0, 3).map((name, index) => (
        <g key={name} transform={`translate(${PLOT.left + index * 150} 20)`}>
          <circle className={`canvas-chart-series-${index}`} cx="0" cy="-4" r="4" />
          <text x="9">{name}</text>
        </g>
      ))}
    </g>
  );
}

function ScatterAxes({
  data,
  minX,
  maxX,
  minY,
  maxY,
}: {
  data: CanvasComponentData;
  minX: number;
  maxX: number;
  minY: number;
  maxY: number;
}) {
  const plotWidth = WIDTH - PLOT.left - PLOT.right;
  return (
    <>
      <text
        className="canvas-chart-axis-title"
        textAnchor="middle"
        x={PLOT.left + plotWidth / 2}
        y={HEIGHT - 8}
      >
        {data.x_label}
      </text>
      <text
        className="canvas-chart-axis-title"
        textAnchor="middle"
        transform={`rotate(-90 14 ${HEIGHT / 2})`}
        x="14"
        y={HEIGHT / 2}
      >
        {data.y_label}
      </text>
      <text className="canvas-chart-tick" textAnchor="start" x={PLOT.left} y={HEIGHT - 35}>
        {formatAxisNumber(minX)}
      </text>
      <text className="canvas-chart-tick" textAnchor="end" x={WIDTH - PLOT.right} y={HEIGHT - 35}>
        {formatAxisNumber(maxX)}
      </text>
      <text className="canvas-chart-tick" textAnchor="end" x={PLOT.left - 8} y={PLOT.top + 4}>
        {formatAxisNumber(maxY)}
      </text>
      <text
        className="canvas-chart-tick"
        textAnchor="end"
        x={PLOT.left - 8}
        y={HEIGHT - PLOT.bottom}
      >
        {formatAxisNumber(minY)}
      </text>
    </>
  );
}

function LineMarks({
  data,
  frame,
  x,
  y,
}: {
  data: CanvasComponentData;
  frame: CanvasComponentFrame;
  x: (value: number) => number;
  y: (value: number) => number;
}) {
  return (
    <>
      <polyline
        className="canvas-chart-line"
        points={frame.values.map((value, index) => `${x(index)},${y(value)}`).join(" ")}
      />
      {frame.values.map((value, index) => (
        <circle
          className="canvas-chart-point"
          cx={x(index)}
          cy={y(value)}
          key={data.labels[index]}
          r="5"
        />
      ))}
    </>
  );
}

function BarMarks({
  data,
  frame,
  baseline,
  y,
}: {
  data: CanvasComponentData;
  frame: CanvasComponentFrame;
  baseline: number;
  y: (value: number) => number;
}) {
  const plotWidth = WIDTH - PLOT.left - PLOT.right;
  const slot = plotWidth / data.labels.length;
  const barWidth = Math.min(64, slot * 0.58);
  return frame.values.map((value, index) => {
    const valueY = y(value);
    return (
      <rect
        className="canvas-chart-bar"
        height={Math.max(Math.abs(baseline - valueY), 1)}
        key={data.labels[index]}
        width={barWidth}
        x={PLOT.left + slot * index + (slot - barWidth) / 2}
        y={Math.min(baseline, valueY)}
      />
    );
  });
}

function CategoryLabels({ data }: { data: CanvasComponentData }) {
  const plotWidth = WIDTH - PLOT.left - PLOT.right;
  return data.labels.map((label, index) => (
    <text
      className="canvas-chart-label"
      key={label}
      textAnchor="middle"
      x={
        data.chart_type === "bar"
          ? PLOT.left + (plotWidth / data.labels.length) * (index + 0.5)
          : PLOT.left + (index / Math.max(data.labels.length - 1, 1)) * plotWidth
      }
      y={HEIGHT - 30}
    >
      {label}
    </text>
  ));
}

function seriesNames(points: CanvasComponentPoint[]) {
  return Array.from(new Set(points.map((point) => point.series || "").filter(Boolean)));
}

function paddedExtent(values: number[]): [number, number] {
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || Math.abs(max) || 1;
  return [min - span * 0.08, max + span * 0.08];
}

function valueExtent(values: number[]): [number, number] {
  const min = Math.min(0, ...values);
  const max = Math.max(0, ...values);
  return max === min ? [min, max + 1] : [min, max];
}

function formatAxisNumber(value: number) {
  return formatChartNumber(Number(value.toFixed(2)));
}
