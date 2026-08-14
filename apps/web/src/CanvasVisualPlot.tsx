import { useId } from "react";

import { formatChartNumber } from "./canvasChartData";
import { visualPlotBounds, visualPlotDescription, type ValidVisualData } from "./canvasVisualData";
import { useI18n } from "./i18n";
import { MathText } from "./MathText";
import type { CanvasComponentPoint, CanvasVisualSeries } from "./types";

const WIDTH = 680;
const HEIGHT = 300;
const LEFT = 54;
const RIGHT = 20;
const TOP = 24;
const BOTTOM = 48;

export function CanvasVisualPlot({ data, title }: { data: ValidVisualData; title: string }) {
  const { t } = useI18n();
  const descriptionId = useId();
  const bounds = visualPlotBounds(data);
  const x = scale(bounds.x, LEFT, WIDTH - RIGHT);
  const y = scale(bounds.y, HEIGHT - BOTTOM, TOP);
  const barSeriesCount = data.visual_series.filter((series) => series.mark === "bar").length;
  let barIndex = 0;
  return (
    <>
      <svg
        aria-describedby={descriptionId}
        aria-label={`${title} plot`}
        className="canvas-visual-plot"
        role="img"
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
      >
        <PlotAxes bounds={bounds} data={data} x={x} y={y} />
        {data.visual_series.map((series, index) => {
          const currentBarIndex = series.mark === "bar" ? barIndex++ : 0;
          return (
            <PlotSeries
              barIndex={currentBarIndex}
              barSeriesCount={barSeriesCount}
              index={index}
              key={`${series.label}-${index}`}
              series={series}
              x={x}
              y={y}
            />
          );
        })}
      </svg>
      <span className="visually-hidden" id={descriptionId}>
        {visualPlotDescription(data)}
      </span>
      <div aria-hidden="true" className="canvas-visual-legend">
        {data.visual_series.map((series, index) => (
          <span className={`canvas-visual-series-${index % 6}`} key={`${series.label}-${index}`}>
            <i />
            {series.label}
          </span>
        ))}
      </div>
      <p aria-hidden="true" className="canvas-visual-scale-summary">
        {data.x_label}: {formatRange(bounds.xDomain)} · {data.y_label}:{" "}
        {formatRange(bounds.yDomain)}
      </p>
      {data.visual_annotations.length ? (
        <aside className="canvas-visual-annotations">
          <strong>{t("component.visual.annotations")}</strong>
          <ul>
            {data.visual_annotations.map((annotation, index) => (
              <li key={index}>
                <MathText allowLinks={false} highlightedText={null} text={annotation.label} />
              </li>
            ))}
          </ul>
        </aside>
      ) : null}
      <VisualDataTable data={data} />
    </>
  );
}

function PlotAxes({
  bounds,
  data,
  x,
  y,
}: {
  bounds: ReturnType<typeof visualPlotBounds>;
  data: ValidVisualData;
  x: (value: number) => number;
  y: (value: number) => number;
}) {
  return (
    <g className="canvas-visual-axes">
      <line x1={LEFT} x2={LEFT} y1={TOP} y2={HEIGHT - BOTTOM} />
      <line x1={LEFT} x2={WIDTH - RIGHT} y1={HEIGHT - BOTTOM} y2={HEIGHT - BOTTOM} />
      <text x={LEFT} y={HEIGHT - 12}>
        {data.x_label}
      </text>
      <text transform={`translate(16 ${HEIGHT - BOTTOM}) rotate(-90)`}>{data.y_label}</text>
      <text x={x(bounds.xDomain[0])} y={HEIGHT - BOTTOM + 20}>
        {formatChartNumber(bounds.xDomain[0])}
      </text>
      <text textAnchor="end" x={x(bounds.xDomain[1])} y={HEIGHT - BOTTOM + 20}>
        {formatChartNumber(bounds.xDomain[1])}
      </text>
      <text textAnchor="end" x={LEFT - 8} y={y(bounds.yDomain[0]) + 4}>
        {formatChartNumber(bounds.yDomain[0])}
      </text>
      <text textAnchor="end" x={LEFT - 8} y={y(bounds.yDomain[1]) + 4}>
        {formatChartNumber(bounds.yDomain[1])}
      </text>
    </g>
  );
}

function PlotSeries({
  barIndex,
  barSeriesCount,
  index,
  series,
  x,
  y,
}: {
  barIndex: number;
  barSeriesCount: number;
  index: number;
  series: CanvasVisualSeries;
  x: (value: number) => number;
  y: (value: number) => number;
}) {
  const className = `canvas-visual-series canvas-visual-series-${index % 6}`;
  if (series.mark === "line") {
    return (
      <g className={className}>
        <polyline points={series.points.map((point) => `${x(point.x)},${y(point.y)}`).join(" ")} />
        {series.points.map((point, pointIndex) => (
          <PlotPoint key={`${point.label}-${pointIndex}`} point={point} x={x} y={y} />
        ))}
      </g>
    );
  }
  if (series.mark === "point") {
    return (
      <g className={className}>
        {series.points.map((point, pointIndex) => (
          <PlotPoint key={`${point.label}-${pointIndex}`} point={point} x={x} y={y} />
        ))}
      </g>
    );
  }
  const width = Math.min(28, 64 / Math.max(barSeriesCount, 1));
  const offset = (barIndex - (barSeriesCount - 1) / 2) * width;
  const baseline = y(0);
  return (
    <g className={className}>
      {series.points.map((point, pointIndex) => {
        const top = Math.min(y(point.y), baseline);
        return (
          <rect
            height={Math.abs(baseline - y(point.y))}
            key={`${point.label}-${pointIndex}`}
            width={Math.max(width - 2, 2)}
            x={x(point.x) + offset - width / 2}
            y={top}
          >
            <title>{pointTitle(point)}</title>
          </rect>
        );
      })}
    </g>
  );
}

function PlotPoint({
  point,
  x,
  y,
}: {
  point: CanvasComponentPoint;
  x: (value: number) => number;
  y: (value: number) => number;
}) {
  return (
    <circle cx={x(point.x)} cy={y(point.y)} r="4">
      <title>{pointTitle(point)}</title>
    </circle>
  );
}

function VisualDataTable({ data }: { data: ValidVisualData }) {
  const { t } = useI18n();
  return (
    <details className="canvas-visual-data">
      <summary>{t("component.visual.data")}</summary>
      <table>
        <thead>
          <tr>
            <th scope="col">{t("component.visual.series")}</th>
            <th scope="col">{t("component.visual.point")}</th>
            <th scope="col">{data.x_label}</th>
            <th scope="col">{data.y_label}</th>
          </tr>
        </thead>
        <tbody>
          {data.visual_series.flatMap((series) =>
            series.points.map((point, index) => (
              <tr key={`${series.label}-${point.label}-${index}`}>
                <th scope="row">{series.label}</th>
                <td>{point.label}</td>
                <td>{formatChartNumber(point.x)}</td>
                <td>{formatChartNumber(point.y)}</td>
              </tr>
            )),
          )}
        </tbody>
      </table>
    </details>
  );
}

function pointTitle(point: CanvasComponentPoint) {
  return `${point.label}: ${formatChartNumber(point.x)}, ${formatChartNumber(point.y)}`;
}

function formatRange([min, max]: readonly [number, number]) {
  return `${formatChartNumber(min)}–${formatChartNumber(max)}`;
}

function scale([min, max]: readonly [number, number], start: number, end: number) {
  const magnitude = Math.max(Math.abs(min), Math.abs(max), Number.MIN_VALUE);
  const normalizedMin = min / magnitude;
  const normalizedSpan = max / magnitude - normalizedMin;
  if (normalizedSpan === 0) return () => (start + end) / 2;
  return (value: number) =>
    start + ((value / magnitude - normalizedMin) / normalizedSpan) * (end - start);
}
