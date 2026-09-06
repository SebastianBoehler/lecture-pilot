import { useI18n } from "./i18n";
import { useMemo } from "react";

import { assetPreviewUrl } from "./assetMedia";
import { AuthenticatedImage } from "./AuthenticatedAsset";
import { LessonDrawerClose } from "./LessonDrawerClose";
import { WorkspaceFileTree } from "./WorkspaceFileTree";
import type { CanvasDocument, LoginSession, WorkspaceResource } from "./types";
import { buildWorkspaceTree } from "./workspaceTree";

export function WorkspaceFilesPanel({
  canvasDocument,
  session,
  selectedResource,
  onClose,
  onSelectResource,
}: {
  canvasDocument: CanvasDocument | null;
  session: LoginSession;
  selectedResource: WorkspaceResource | null;
  onClose: () => void;
  onSelectResource: (resource: WorkspaceResource) => void;
}) {
  const { t } = useI18n();
  const nodes = useMemo(
    () => (canvasDocument ? buildWorkspaceTree(canvasDocument) : []),
    [canvasDocument],
  );

  return (
    <aside className="drawer" id="lesson-panel" aria-label="File workspace panel">
      <LessonDrawerClose returnFocusId="lesson-panel-trigger-files" onClose={onClose} />
      <div className="drawer-section">
        <h2>Workspace files</h2>
        {canvasDocument ? (
          <>
            <WorkspacePreview selectedResource={selectedResource} session={session} />
            <details className="workspace-browser">
              <summary>{t("files.browse")}</summary>
              <WorkspaceFileTree
                nodes={nodes}
                selectedResource={selectedResource}
                onSelectResource={onSelectResource}
              />
            </details>
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
  if (!selectedResource)
    return <p className="drawer-note">Open a source from the canvas, or browse the files below.</p>;
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
