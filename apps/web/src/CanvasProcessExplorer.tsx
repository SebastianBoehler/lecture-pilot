import { useState, type ReactNode } from "react";

import { useI18n } from "./i18n";
import type { CanvasBlock } from "./types";

type ProcessExplorerProps = {
  block: CanvasBlock;
  className: string;
  sourceMarker: ReactNode;
};

export function ProcessExplorer({ block, className, sourceMarker }: ProcessExplorerProps) {
  const { t } = useI18n();
  const steps = block.component_data?.steps ?? [];
  const [activeIndex, setActiveIndex] = useState(0);
  if (steps.length < 2) {
    return (
      <aside className={`${className} canvas-component canvas-component-unsupported`} id={block.id}>
        <strong>{block.caption || t("component.process.title")}</strong>
        <p>{t("component.process.invalid")}</p>
      </aside>
    );
  }
  const safeIndex = Math.min(activeIndex, steps.length - 1);
  const active = steps[safeIndex];

  return (
    <section className={`${className} canvas-component canvas-process-explorer`} id={block.id}>
      <header className="canvas-component-header">
        <h3>{block.caption || t("component.process.title")}</h3>
        {block.text ? <p>{block.text}</p> : null}
      </header>
      <ol className="canvas-process-steps">
        {steps.map((step, index) => (
          <li key={`${index}-${step.title}`}>
            <button
              aria-label={`${index + 1} ${step.title}`}
              aria-current={index === safeIndex ? "step" : undefined}
              onClick={() => setActiveIndex(index)}
              type="button"
            >
              <span>{index + 1}</span>
              {step.title}
            </button>
          </li>
        ))}
      </ol>
      <div className="canvas-process-detail" aria-live="polite">
        <span>
          {t("component.process.progress", {
            current: safeIndex + 1,
            total: steps.length,
          })}
        </span>
        <h4>{active.title}</h4>
        <p>{active.text}</p>
      </div>
      {sourceMarker}
    </section>
  );
}
