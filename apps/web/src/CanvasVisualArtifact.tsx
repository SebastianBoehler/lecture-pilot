import type { ReactNode } from "react";

import { CanvasVisualPlot } from "./CanvasVisualPlot";
import { validVisualArtifact, type ValidVisualData } from "./canvasVisualData";
import { useI18n } from "./i18n";
import { MathText } from "./MathText";
import type { CanvasBlock, CanvasVisualAnnotation } from "./types";

type VisualArtifactProps = {
  block: CanvasBlock;
  className: string;
  sourceMarker: ReactNode;
};

export function VisualArtifact({ block, className, sourceMarker }: VisualArtifactProps) {
  const { t } = useI18n();
  const data = block.component_data;
  if (block.component_version !== 1 || !validVisualArtifact(data)) {
    return <InvalidVisual block={block} className={className} />;
  }
  const title = block.caption || t("component.visual.title");
  const titleId = `${block.id}-title`;
  return (
    <section
      aria-labelledby={titleId}
      className={`${className} canvas-component canvas-visual-artifact is-${data.visual_layout}`}
      id={block.id}
    >
      <header className="canvas-component-header">
        <h3 id={titleId}>{title}</h3>
        {block.text ? (
          <p>
            <MathText allowLinks={false} highlightedText={null} text={block.text} />
          </p>
        ) : null}
      </header>
      {data.visual_layout === "plot" ? (
        <CanvasVisualPlot data={data} title={title} />
      ) : (
        <NodeVisual data={data} title={title} />
      )}
      {sourceMarker}
    </section>
  );
}

function NodeVisual({ data, title }: { data: ValidVisualData; title: string }) {
  const { t } = useI18n();
  const globalAnnotations = data.visual_annotations.filter((item) => !item.target_id);
  return (
    <>
      <ol aria-label={title} className="canvas-visual-nodes">
        {data.visual_nodes.map((node, index) => (
          <li className="canvas-visual-node" key={node.id}>
            {data.visual_layout === "timeline" ? (
              <span className="canvas-visual-index" aria-hidden="true">
                {index + 1}
              </span>
            ) : null}
            <article>
              <h4>
                <MathText allowLinks={false} highlightedText={null} text={node.label} />
              </h4>
              {node.value ? <strong>{node.value}</strong> : null}
              <p>
                <MathText allowLinks={false} highlightedText={null} text={node.detail} />
              </p>
              <Annotations
                annotations={data.visual_annotations.filter(
                  (annotation) => annotation.target_id === node.id,
                )}
              />
            </article>
          </li>
        ))}
      </ol>
      {data.visual_edges.length ? (
        <div className="canvas-visual-relationships">
          <strong>{t("component.visual.relationships")}</strong>
          <ul>
            {data.visual_edges.map((edge, index) => (
              <li key={`${edge.from_id}-${edge.to_id}-${index}`}>
                <span>{nodeLabel(data, edge.from_id)}</span>
                <span aria-hidden="true">→</span>
                {edge.label ? <span className="canvas-visual-edge-label">{edge.label}</span> : null}
                <span>{nodeLabel(data, edge.to_id)}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      <Annotations annotations={globalAnnotations} titled />
    </>
  );
}

function Annotations({
  annotations,
  titled = false,
}: {
  annotations: CanvasVisualAnnotation[];
  titled?: boolean;
}) {
  const { t } = useI18n();
  if (!annotations.length) return null;
  return (
    <aside className="canvas-visual-annotations">
      {titled ? <strong>{t("component.visual.annotations")}</strong> : null}
      <ul>
        {annotations.map((annotation, index) => (
          <li key={`${annotation.target_id ?? "global"}-${index}`}>
            <MathText allowLinks={false} highlightedText={null} text={annotation.label} />
          </li>
        ))}
      </ul>
    </aside>
  );
}

function nodeLabel(data: ValidVisualData, id: string) {
  return data.visual_nodes.find((node) => node.id === id)?.label ?? id;
}

function InvalidVisual({ block, className }: { block: CanvasBlock; className: string }) {
  const { t } = useI18n();
  return (
    <aside className={`${className} canvas-component canvas-component-unsupported`} id={block.id}>
      <strong>{block.caption || t("component.visual.title")}</strong>
      <p>{t("component.visual.invalid")}</p>
    </aside>
  );
}
