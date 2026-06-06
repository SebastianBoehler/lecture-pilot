import { apiUrl } from "./api";
import type { CanvasBlock, CanvasDocument, Lecture, WorkspaceResource } from "./types";

export function WorkspaceFilesPanel({
  canvasDocument,
  lecture,
  selectedResource,
  onSelectResource,
}: {
  canvasDocument: CanvasDocument | null;
  lecture: Lecture;
  selectedResource: WorkspaceResource | null;
  onSelectResource: (resource: WorkspaceResource) => void;
}) {
  const assets = canvasDocument ? uniqueAssets(canvasDocument) : [];
  const lectureSource = lecture.materialPath ?? "courses/martius-ml/lectures/03/source.tex";
  return (
    <aside className="drawer" aria-label="File workspace panel">
      <div className="drawer-section">
        <h2>Workspace files</h2>
        {canvasDocument ? (
          <>
            <WorkspacePreview selectedResource={selectedResource} />
            <div className="workspace-files">
              <FileEntry
                resource={{
                  id: "student-canvas",
                  kind: "canvas",
                  label: "Student canvas",
                  path: canvasDocument.workspace_path,
                }}
                selectedResource={selectedResource}
                onSelectResource={onSelectResource}
              />
              <FileEntry
                resource={{
                  id: "original-source",
                  kind: "source",
                  label: "Original source",
                  path: canvasDocument.source_ref,
                }}
                selectedResource={selectedResource}
                onSelectResource={onSelectResource}
              />
              <FileEntry
                resource={{ id: "lecture-material", kind: "source", label: "Lecture material", path: lectureSource }}
                selectedResource={selectedResource}
                onSelectResource={onSelectResource}
              />
            </div>
            <WorkspaceSectionRefs canvasDocument={canvasDocument} />
            <WorkspaceAssets assets={assets} selectedResource={selectedResource} onSelectResource={onSelectResource} />
          </>
        ) : (
          <p className="drawer-note">Canvas loading...</p>
        )}
      </div>
    </aside>
  );
}

function FileEntry({
  resource,
  selectedResource,
  onSelectResource,
}: {
  resource: WorkspaceResource;
  selectedResource: WorkspaceResource | null;
  onSelectResource: (resource: WorkspaceResource) => void;
}) {
  const isSelected = selectedResource?.path === resource.path;
  return (
    <button
      aria-pressed={isSelected}
      className={isSelected ? "workspace-file is-selected" : "workspace-file"}
      type="button"
      onClick={() => onSelectResource(resource)}
    >
      <span>{resource.label}</span>
      <code>{resource.path}</code>
    </button>
  );
}

function WorkspaceSectionRefs({ canvasDocument }: { canvasDocument: CanvasDocument }) {
  return (
    <section className="workspace-block" aria-labelledby="workspace-section-refs">
      <h3 id="workspace-section-refs">Section references</h3>
      <ul>
        {canvasDocument.sections.map((section) => (
          <li key={section.id}>
            <strong>{section.title}</strong>
            <code>{section.source_ref ?? section.id}</code>
          </li>
        ))}
      </ul>
    </section>
  );
}

function WorkspaceAssets({
  assets,
  selectedResource,
  onSelectResource,
}: {
  assets: CanvasBlock[];
  selectedResource: WorkspaceResource | null;
  onSelectResource: (resource: WorkspaceResource) => void;
}) {
  return (
    <section className="workspace-block" aria-labelledby="workspace-assets">
      <h3 id="workspace-assets">Course assets</h3>
      {assets.length ? (
        <ul>
          {assets.map((asset) => (
            <li key={asset.id}>
              <FileEntry resource={assetResource(asset)} selectedResource={selectedResource} onSelectResource={onSelectResource} />
            </li>
          ))}
        </ul>
      ) : (
        <p className="drawer-note">No linked assets in this canvas yet.</p>
      )}
    </section>
  );
}

function WorkspacePreview({ selectedResource }: { selectedResource: WorkspaceResource | null }) {
  if (!selectedResource) return <p className="drawer-note">Select a file to preview it here.</p>;
  return (
    <section className="workspace-preview" aria-label="Selected file preview">
      <span>{previewLabel(selectedResource.kind)}</span>
      <strong>{selectedResource.label}</strong>
      {selectedResource.detail ? (
        <p className="workspace-preview-trace">
          <span>Trace target</span>
          <strong>{selectedResource.detail}</strong>
        </p>
      ) : null}
      {selectedResource.url ? (
        <img alt={selectedResource.label} src={apiUrl(selectedResource.url)} />
      ) : (
        <code>{selectedResource.path}</code>
      )}
    </section>
  );
}

function previewLabel(kind: WorkspaceResource["kind"]) {
  if (kind === "source") return "Source trace";
  if (kind === "asset") return "Asset preview";
  return "Canvas file";
}

function assetResource(asset: CanvasBlock): WorkspaceResource {
  return {
    id: asset.id,
    kind: "asset",
    label: asset.asset_path ?? asset.caption ?? asset.id,
    path: asset.asset_path ?? asset.caption ?? asset.id,
    url: asset.asset_url,
  };
}

function uniqueAssets(canvasDocument: CanvasDocument) {
  const byPath = new Map<string, CanvasBlock>();
  for (const section of canvasDocument.sections) {
    for (const block of section.blocks) {
      const key = block.asset_path ?? block.asset_url;
      if (key && !byPath.has(key)) byPath.set(key, block);
    }
  }
  return [...byPath.values()];
}
