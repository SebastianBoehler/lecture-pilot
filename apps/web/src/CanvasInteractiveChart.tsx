import { useState, type ReactNode } from "react";

import { CanvasChartControl } from "./CanvasChartControl";
import { ChartDataTable } from "./CanvasChartDataTable";
import { ChartGraphic } from "./CanvasChartGraphic";
import { validChartData } from "./canvasChartData";
import { useI18n } from "./i18n";
import type { CanvasBlock } from "./types";

type InteractiveChartProps = {
  block: CanvasBlock;
  className: string;
  sourceMarker: ReactNode;
};

export function InteractiveChart({ block, className, sourceMarker }: InteractiveChartProps) {
  const { t } = useI18n();
  const data = validChartData(block.component_data) ? block.component_data : null;
  const [frameIndex, setFrameIndex] = useState(0);
  if (!data) return <InvalidChart block={block} className={className} />;
  const safeFrameIndex = Math.min(frameIndex, data.frames.length - 1);
  const frame = data.frames[safeFrameIndex];
  const title = block.caption || t("component.chart.title");

  return (
    <section className={`${className} canvas-component canvas-interactive-chart`} id={block.id}>
      <header className="canvas-component-header">
        <span className="canvas-learning-label">{t("component.chart.label")}</span>
        <h3>{title}</h3>
        {block.text ? <p>{block.text}</p> : null}
      </header>

      {data.frames.length > 1 ? (
        <CanvasChartControl
          activeIndex={safeFrameIndex}
          controlLabel={data.control_label || t("component.chart.frame")}
          data={data}
          onChange={setFrameIndex}
        />
      ) : null}

      <ChartGraphic
        ariaLabel={t("component.chart.atFrame", { title, frame: frame.label })}
        data={data}
        frame={frame}
      />
      <p className="canvas-chart-explanation" aria-live="polite">
        {frame.explanation}
      </p>
      <ChartDataTable data={data} frame={frame} />
      {sourceMarker}
    </section>
  );
}

function InvalidChart({ block, className }: { block: CanvasBlock; className: string }) {
  const { t } = useI18n();
  return (
    <aside className={`${className} canvas-component canvas-component-unsupported`} id={block.id}>
      <strong>{block.caption || t("component.chart.title")}</strong>
      <p>{t("component.chart.invalid")}</p>
    </aside>
  );
}
