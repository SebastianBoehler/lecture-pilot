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
  return (
    <footer className="section-sources" aria-label={`${section.title} source references`}>
      <span>Sources</span>
      <ol aria-label={`${section.title} source list`}>
        {references.map((reference) => (
          <li key={reference.resource.id}>
            <SourceButton reference={reference} onOpenResource={onOpenResource} />
          </li>
        ))}
      </ol>
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
    <button className="source-reference" type="button" onClick={() => onOpenResource(resource)}>
      <span>[{reference.number}]</span>
      <code>{resource.path}</code>
      {resource.detail ? <small>{resource.detail}</small> : null}
    </button>
  );
}
