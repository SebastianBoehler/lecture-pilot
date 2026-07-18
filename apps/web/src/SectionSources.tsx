import type { CanvasDocument, CanvasSection, WorkspaceResource } from "./types";
import { sectionSourceReferences } from "./sourceReferences";

export function SectionSources({
  canvasDocument,
  section,
  onOpenResource,
}: {
  canvasDocument: CanvasDocument;
  section: CanvasSection;
  onOpenResource: (resource: WorkspaceResource) => void;
}) {
  const references = sectionSourceReferences(canvasDocument, section);
  const primary = references[0]?.resource;
  return (
    <footer className="section-sources" aria-label={`${section.title} source references`}>
      <details>
        <summary>
          <span className="source-heading">Evidence</span>
          <span className="source-summary">
            <strong>{primary?.label ?? "Course material"}</strong>
            {primary?.detail ? <small>{primary.detail}</small> : null}
          </span>
          <span className="source-count">
            {references.length} {references.length === 1 ? "source" : "sources"}
          </span>
        </summary>
        <ol aria-label={`${section.title} source list`}>
          {references.map((reference) => (
            <li key={reference.resource.id}>
              <SourceButton reference={reference} onOpenResource={onOpenResource} />
            </li>
          ))}
        </ol>
      </details>
    </footer>
  );
}

function SourceButton({
  reference,
  onOpenResource,
}: {
  reference: ReturnType<typeof sectionSourceReferences>[number];
  onOpenResource: (resource: WorkspaceResource) => void;
}) {
  const resource = reference.resource;
  return (
    <button
      aria-label={`Open ${resource.label} source`}
      className="source-reference"
      type="button"
      onClick={() => onOpenResource(resource)}
    >
      <span className="source-index">{String(reference.number).padStart(2, "0")}</span>
      <span className="source-copy">
        <strong>{resource.label}</strong>
        <small>
          {sourceType(resource)}
          {resource.detail ? ` · ${resource.detail}` : ""}
        </small>
      </span>
      <span aria-hidden="true" className="source-open">
        Open
      </span>
    </button>
  );
}

function sourceType(resource: ReturnType<typeof sectionSourceReferences>[number]["resource"]) {
  if (resource.kind === "video") return "Video";
  if (resource.kind === "asset" && resource.url) return "Course media";
  const suffix = resource.path.split(".").at(-1)?.toLowerCase();
  if (suffix === "tex" || suffix === "sty") return "LaTeX";
  if (suffix === "pdf") return "PDF";
  if (suffix === "md") return "Notes";
  if (suffix === "txt") return "Transcript";
  if (["png", "jpg", "jpeg", "svg", "webp", "gif"].includes(suffix ?? "")) return "Image";
  if (["mp4", "webm"].includes(suffix ?? "")) return "Video";
  return suffix?.toUpperCase() || "Course source";
}
