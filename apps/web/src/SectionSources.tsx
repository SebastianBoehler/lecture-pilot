import type { CanvasDocument, CanvasSection, WorkspaceResource } from "./types";

export function SectionSources({
  canvasDocument,
  section,
  onOpenResource,
}: {
  canvasDocument: CanvasDocument;
  section: CanvasSection;
  onOpenResource: (resource: WorkspaceResource) => void;
}) {
  const assets = section.blocks.filter((block) => block.asset_path || block.asset_url);
  return (
    <footer className="section-sources" aria-label={`${section.title} source references`}>
      <span>Sources</span>
      <div className="source-token-list">
        <SourceButton
          label="Lecture source"
          resource={{
            id: `source-${canvasDocument.source_ref}`,
            kind: "source",
            label: canvasDocument.source_ref,
            path: canvasDocument.source_ref,
          }}
          onOpenResource={onOpenResource}
        />
        {section.source_ref ? <SourceToken label="Section reference" value={section.source_ref} /> : null}
      </div>
      {assets.length ? (
        <ul aria-label={`${section.title} asset paths`}>
          {assets.map((asset) => (
            <li key={asset.id}>
              <SourceButton
                label="Asset"
                resource={{
                  id: asset.id,
                  kind: "asset",
                  label: asset.asset_path ?? asset.caption ?? asset.id,
                  path: asset.asset_path ?? asset.caption ?? asset.id,
                  url: asset.asset_url,
                }}
                onOpenResource={onOpenResource}
              />
            </li>
          ))}
        </ul>
      ) : null}
    </footer>
  );
}

function SourceButton({
  label,
  resource,
  onOpenResource,
}: {
  label: string;
  resource: WorkspaceResource;
  onOpenResource: (resource: WorkspaceResource) => void;
}) {
  return (
    <button className="source-token source-button" type="button" onClick={() => onOpenResource(resource)}>
      <span>{label}</span>
      <code>{resource.path}</code>
    </button>
  );
}

function SourceToken({ label, value }: { label: string; value: string }) {
  return (
    <span className="source-token">
      <span>{label}</span>
      <code>{value}</code>
    </span>
  );
}
