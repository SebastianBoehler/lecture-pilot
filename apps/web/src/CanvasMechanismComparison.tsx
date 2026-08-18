import type { ReactNode } from "react";

import { formatChartNumber } from "./canvasChartData";
import { useI18n } from "./i18n";
import { MathText } from "./MathText";
import type { CanvasBlock, CanvasComponentFrame, CanvasComponentPoint } from "./types";

type MechanismComparisonProps = {
  block: CanvasBlock;
  className: string;
  sourceMarker: ReactNode;
};

const PROFILE_WIDTH = 320;
const PROFILE_HEIGHT = 126;
const PROFILE_INSET = 14;

export function MechanismComparison({ block, className, sourceMarker }: MechanismComparisonProps) {
  const { t } = useI18n();
  const data = block.component_data;
  const valid =
    data &&
    data.frames.length >= 2 &&
    data.frames.length <= 4 &&
    data.labels.length >= 2 &&
    data.frames.every((frame) => frame.values.length === data.labels.length);
  if (!valid) return <InvalidComparison block={block} className={className} />;
  const title = block.caption || t("component.comparison.title");
  const titleId = `${block.id}-title`;
  const profileBounds = comparisonBounds(data.frames);

  return (
    <section
      aria-labelledby={titleId}
      className={`${className} canvas-component canvas-mechanism-comparison`}
      id={block.id}
    >
      <header className="canvas-component-header">
        <h3 id={titleId}>{title}</h3>
        {block.text ? (
          <p>
            <MathText highlightedText={null} text={block.text} />
          </p>
        ) : null}
      </header>
      <div className="canvas-mechanism-grid">
        {data.frames.map((frame) => (
          <article className="canvas-mechanism" key={frame.label}>
            <h4>
              <MathText highlightedText={null} text={frame.label} />
            </h4>
            {frame.points?.length ? (
              <MechanismProfile
                ariaLabel={t("component.comparison.profile", { mechanism: frame.label })}
                bounds={profileBounds}
                points={frame.points}
                xLabel={data.x_label}
                yLabel={data.y_label}
              />
            ) : null}
            <p>
              <MathText highlightedText={null} text={frame.explanation} />
            </p>
          </article>
        ))}
      </div>
      <ComparisonTable
        frames={data.frames}
        labels={data.labels}
        title={t("component.comparison.outcomes")}
      />
      {sourceMarker}
    </section>
  );
}

function MechanismProfile({
  ariaLabel,
  bounds,
  points,
  xLabel,
  yLabel,
}: {
  ariaLabel: string;
  bounds: ProfileBounds;
  points: CanvasComponentPoint[];
  xLabel: string | null;
  yLabel: string | null;
}) {
  const [minX, maxX] = bounds.x;
  const [minY, maxY] = bounds.y;
  const x = (value: number) => scale(value, minX, maxX, PROFILE_WIDTH);
  const y = (value: number) => PROFILE_HEIGHT - scale(value, minY, maxY, PROFILE_HEIGHT);
  const path = points.map((point) => `${x(point.x)},${y(point.y)}`).join(" ");
  return (
    <div className="canvas-mechanism-profile-wrap">
      <svg
        aria-label={ariaLabel}
        className="canvas-mechanism-profile"
        role="img"
        viewBox="0 0 320 126"
      >
        <polyline points={path} />
        {points.map((point, index) => (
          <circle cx={x(point.x)} cy={y(point.y)} key={`${point.label}-${index}`} r="4">
            <title>
              {point.label}: {formatChartNumber(point.y)}
            </title>
          </circle>
        ))}
      </svg>
      <div className="canvas-mechanism-axes">
        <span>{yLabel}</span>
        <span>{xLabel}</span>
      </div>
    </div>
  );
}

function ComparisonTable({
  frames,
  labels,
  title,
}: {
  frames: CanvasComponentFrame[];
  labels: string[];
  title: string;
}) {
  return (
    <div className="canvas-mechanism-table">
      <strong>{title}</strong>
      <table>
        <thead>
          <tr>
            <th scope="col" />
            {frames.map((frame) => (
              <th key={frame.label} scope="col">
                {frame.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {labels.map((label, labelIndex) => (
            <tr key={label}>
              <th scope="row">{label}</th>
              {frames.map((frame) => (
                <td key={frame.label}>{formatChartNumber(frame.values[labelIndex])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function InvalidComparison({ block, className }: { block: CanvasBlock; className: string }) {
  const { t } = useI18n();
  return (
    <aside className={`${className} canvas-component canvas-component-unsupported`} id={block.id}>
      <strong>{block.caption || t("component.comparison.title")}</strong>
      <p>{t("component.comparison.invalid")}</p>
    </aside>
  );
}

function extent(values: number[]): [number, number] {
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || Math.abs(max) || 1;
  return [min - span * 0.08, max + span * 0.08];
}

type ProfileBounds = { x: [number, number]; y: [number, number] };

function comparisonBounds(frames: CanvasComponentFrame[]): ProfileBounds {
  const points = frames.flatMap((frame) => frame.points ?? []);
  return {
    x: extent(points.map((point) => point.x)),
    y: extent(points.map((point) => point.y)),
  };
}

function scale(value: number, min: number, max: number, size: number) {
  return PROFILE_INSET + ((value - min) / (max - min)) * (size - PROFILE_INSET * 2);
}
