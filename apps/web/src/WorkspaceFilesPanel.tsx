import { useMemo } from "react";

import { assetPreviewUrl } from "./assetMedia";
import { AuthenticatedImage } from "./AuthenticatedAsset";
import { WorkspaceFileTree } from "./WorkspaceFileTree";
import type { CanvasDocument, LoginSession, WorkspaceResource } from "./types";
import { buildWorkspaceTree } from "./workspaceTree";

export function WorkspaceFilesPanel({
  canvasDocument,
  session,
  selectedResource,
  onSelectResource,
}: {
  canvasDocument: CanvasDocument | null;
  session: LoginSession;
  selectedResource: WorkspaceResource | null;
  onSelectResource: (resource: WorkspaceResource) => void;
}) {
  const nodes = useMemo(
    () => (canvasDocument ? buildWorkspaceTree(canvasDocument) : []),
    [canvasDocument],
  );

  return (
    <aside className="drawer" aria-label="File workspace panel">
      <div className="drawer-section">
        <h2>Workspace files</h2>
        {canvasDocument ? (
          <>
            <WorkspaceFileTree
              nodes={nodes}
              selectedResource={selectedResource}
              onSelectResource={onSelectResource}
            />
            <WorkspacePreview selectedResource={selectedResource} session={session} />
          </>
        ) : (
          <p className="drawer-note">Canvas loading...</p>
        )}
      </div>
    </aside>
  );
}

function WorkspacePreview({
  selectedResource,
  session,
}: {
  selectedResource: WorkspaceResource | null;
  session: LoginSession;
}) {
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
        selectedResource.kind === "video" ? (
          <VideoPreview label={selectedResource.label} url={selectedResource.url} />
        ) : (
          <AuthenticatedImage
            alt={selectedResource.label}
            session={session}
            src={assetPreviewUrl(selectedResource.url, selectedResource.path)}
          />
        )
      ) : (
        <code>{selectedResource.displayPath ?? selectedResource.path}</code>
      )}
    </section>
  );
}

function previewLabel(kind: WorkspaceResource["kind"]) {
  if (kind === "memory") return "Memory file";
  if (kind === "source") return "Source file";
  if (kind === "video") return "Video preview";
  if (kind === "asset") return "Asset preview";
  return "Canvas file";
}

function VideoPreview({ label, url }: { label: string; url: string }) {
  const embedUrl = youtubeEmbedUrl(url);
  if (!embedUrl) {
    return (
      <a href={url} rel="noreferrer" target="_blank">
        Open video
      </a>
    );
  }
  return (
    <iframe
      allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
      allowFullScreen
      src={embedUrl}
      title={label}
    />
  );
}

function youtubeEmbedUrl(url: string) {
  try {
    const parsed = new URL(url);
    const parts = parsed.pathname.split("/").filter(Boolean);
    const videoId = parsed.hostname.endsWith("youtu.be") ? parts[0] : parsed.searchParams.get("v");
    if (!videoId || !/^[A-Za-z0-9_-]{11}$/.test(videoId)) return null;
    return `https://www.youtube-nocookie.com/embed/${videoId}`;
  } catch {
    return null;
  }
}
