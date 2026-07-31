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
  const title = processTitle(block, t("component.process.title"));

  return (
    <section className={`${className} canvas-component canvas-process-explorer`} id={block.id}>
      <header className="canvas-component-header">
        <h3>{title}</h3>
        {block.text ? <p>{block.text}</p> : null}
      </header>
      <ol className={`canvas-process-steps${steps.length === 5 ? " is-five-step" : ""}`}>
        {steps.map((step, index) => (
          <li key={`${index}-${step.title}`}>
            <button
              aria-label={`${index + 1} ${step.title}`}
              aria-current={index === safeIndex ? "step" : undefined}
              onClick={() => setActiveIndex(index)}
              type="button"
            >
              <span className="canvas-process-step-number">{index + 1}</span>
              <span className="canvas-process-step-title">{step.title}</span>
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

function processTitle(block: CanvasBlock, fallback: string): string {
  const caption = block.caption?.trim();
  if (caption && !/\.ya?ml$/i.test(caption)) {
    return caption;
  }
  const source = block.component_id || caption || block.component_ref;
  const stem =
    source
      ?.split("/")
      .pop()
      ?.replace(/\.[^.]+$/, "") ?? "";
  const words = stem.split(/[-_\s]+/).filter(Boolean);
  if (
    words.length > 1 &&
    ["component", "explorer", "process"].includes(words.at(-1)!.toLowerCase())
  ) {
    words.pop();
  }
  const acronyms = new Set(["ai", "api", "llm", "nlp", "ui", "ux"]);
  const title = words
    .map((word, index) =>
      acronyms.has(word.toLowerCase()) ? word.toUpperCase() : index === 0 ? capitalize(word) : word,
    )
    .join(" ");
  return title || fallback;
}

function capitalize(value: string): string {
  return `${value.charAt(0).toUpperCase()}${value.slice(1)}`;
}
