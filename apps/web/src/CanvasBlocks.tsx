import { apiUrl } from "./api";
import { assetPreviewUrl } from "./assetMedia";
import { DisplayMath, MathText } from "./MathText";
import { SourceMarker } from "./SourceMarker";
import { blockSourceReference, sectionSourceReferences } from "./sourceReferences";
import type { CanvasBlock, CanvasDocument, CanvasSection, DocumentAnchorId, WorkspaceResource } from "./types";

type CanvasBlocksProps = {
  canvasDocument: CanvasDocument;
  section: CanvasSection;
  highlightedBlockId: string | null;
  highlightedText: string | null;
  outlinePulseId: DocumentAnchorId | null;
  outlinePulseVersion: number;
  onOpenResource: (resource: WorkspaceResource) => void;
};

type RenderBlockOptions = {
  highlightedBlockId: string | null;
  highlightedText: string | null;
  outlinePulseId: DocumentAnchorId | null;
  outlinePulseVersion: number;
  onOpenResource: (resource: WorkspaceResource) => void;
  sourceLabel: string;
  sourceReferences: ReturnType<typeof sectionSourceReferences>;
  keySourceBlockId: string | null;
};

export function CanvasBlocks({
  canvasDocument,
  section,
  highlightedBlockId,
  highlightedText,
  outlinePulseId,
  outlinePulseVersion,
  onOpenResource,
}: CanvasBlocksProps) {
  return renderBlocks(section.blocks, {
    highlightedBlockId,
    highlightedText,
    outlinePulseId,
    outlinePulseVersion,
    onOpenResource,
    sourceLabel: section.title,
    sourceReferences: sectionSourceReferences(canvasDocument, section),
    keySourceBlockId: findKeySourceBlockId(section.blocks),
  });
}

function renderBlocks(blocks: CanvasBlock[], options: RenderBlockOptions) {
  const rendered = [];
  for (let index = 0; index < blocks.length; index += 1) {
    const block = blocks[index];
    if (block.type === "math") {
      const run = readBlockRun(blocks, index, "math");
      if (run.length > 1) {
        rendered.push(renderDerivationRun(run, options));
        index += run.length - 1;
        continue;
      }
    }
    if (block.type === "paragraph") {
      const run = readBlockRun(blocks, index, "paragraph");
      if (run.length > 2) {
        rendered.push(renderProseRun(run, options));
        index += run.length - 1;
        continue;
      }
    }
    rendered.push(renderBlockWithOptions(block, options));
  }
  return rendered;
}

function renderDerivationRun(blocks: CanvasBlock[], options: RenderBlockOptions) {
  return (
    <div className="canvas-derivation" key={`${blocks[0].id}-run`}>
      <div className="canvas-derivation-header">Derivation</div>
      {blocks.map((block, index) => (
        <div className="canvas-derivation-row" key={block.id}>
          <span className="canvas-step-number">{index + 1}</span>
          {renderBlockWithOptions(block, options)}
        </div>
      ))}
    </div>
  );
}

function renderProseRun(blocks: CanvasBlock[], options: RenderBlockOptions) {
  return (
    <div className="canvas-prose-run" key={`${blocks[0].id}-run`}>
      {blocks.map((block) => renderBlockWithOptions(block, options))}
    </div>
  );
}

function readBlockRun(blocks: CanvasBlock[], start: number, type: CanvasBlock["type"]) {
  const run = [];
  for (let index = start; index < blocks.length && blocks[index].type === type; index += 1) {
    run.push(blocks[index]);
  }
  return run;
}

function renderBlockWithOptions(block: CanvasBlock, options: RenderBlockOptions) {
  return renderBlock(block, {
    isHighlighted: options.highlightedBlockId === block.id,
    isPulsed: options.outlinePulseId === block.id,
    highlightedText: options.highlightedText,
    outlinePulseVersion: options.outlinePulseVersion,
    onOpenResource: options.onOpenResource,
    showSourceMarker: shouldShowSourceMarker(block, options.keySourceBlockId),
    sourceLabel: options.sourceLabel,
    sourceReference: blockSourceReference(options.sourceReferences, block),
  });
}

function renderBlock(
  block: CanvasBlock,
  {
    isHighlighted,
    isPulsed,
    highlightedText,
    outlinePulseVersion,
    onOpenResource,
    showSourceMarker,
    sourceLabel,
    sourceReference,
  }: {
    isHighlighted: boolean;
    isPulsed: boolean;
    highlightedText: string | null;
    outlinePulseVersion: number;
    onOpenResource: (resource: WorkspaceResource) => void;
    showSourceMarker: boolean;
    sourceLabel: string;
    sourceReference: ReturnType<typeof sectionSourceReferences>[number];
  },
) {
  const className = [
    "canvas-block",
    isHighlighted ? "is-highlighted" : "",
    pulseClass(isPulsed, outlinePulseVersion),
  ]
    .filter(Boolean)
    .join(" ");
  const phrase = isHighlighted ? highlightedText : null;
  const sourceMarker = showSourceMarker ? (
    <SourceMarker label={sourceLabel} reference={sourceReference} onOpenResource={onOpenResource} />
  ) : null;
  if (block.type === "list") {
    return (
      <ul className={`${className} canvas-list`} id={block.id} key={block.id}>
        {block.items.map((item, index) => (
          <li key={item}>
            <MathText highlightedText={phrase} text={item} />
            {index === block.items.length - 1 ? sourceMarker : null}
          </li>
        ))}
      </ul>
    );
  }

  if (block.type === "asset" && block.asset_url) {
    const url = apiUrl(block.asset_url);
    const caption = block.caption ?? "Course figure";
    return (
      <figure className={`${className} canvas-asset`} id={block.id} key={block.id}>
        <img alt={caption} src={assetPreviewUrl(url, block.asset_path ?? block.asset_url)} />
        <figcaption>
          {block.caption}
          {sourceMarker}
        </figcaption>
      </figure>
    );
  }

  if (block.type === "video" && block.asset_url) {
    const embedUrl = youtubeEmbedUrl(block.asset_url);
    const title = block.caption ?? "YouTube video";
    return (
      <figure className={`${className} canvas-video`} id={block.id} key={block.id}>
        <div className="canvas-video-frame">
          {embedUrl ? (
            <iframe
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
              allowFullScreen
              src={embedUrl}
              title={title}
            />
          ) : (
            <a href={block.asset_url} rel="noreferrer" target="_blank">
              Open video
            </a>
          )}
        </div>
        <figcaption>
          <strong>{title}</strong>
          {block.text ? <span>{block.text}</span> : null}
          {sourceMarker}
        </figcaption>
      </figure>
    );
  }

  if (block.type === "callout") {
    return (
      <aside className={`${className} canvas-callout`} id={block.id} key={block.id}>
        <MathText highlightedText={phrase} text={block.text ?? ""} />
        {sourceMarker}
      </aside>
    );
  }

  if (block.type === "math" && block.text) {
    return (
      <div className={`${className} canvas-math`} id={block.id} key={block.id}>
        <DisplayMath expression={block.text} />
        {sourceMarker}
      </div>
    );
  }

  return (
    <p className={`${className} canvas-paragraph`} id={block.id} key={block.id}>
      <MathText highlightedText={phrase} text={block.text ?? ""} />
      {sourceMarker}
    </p>
  );
}

function pulseClass(isPulsed: boolean, version: number) {
  if (!isPulsed) return "";
  return `is-outline-pulsed pulse-${version % 2 === 0 ? "even" : "odd"}`;
}

function findKeySourceBlockId(blocks: CanvasBlock[]) {
  return (
    blocks.find((block) => block.type === "callout")?.id ??
    blocks.find((block) => block.type === "list")?.id ??
    blocks.find((block) => block.type === "paragraph")?.id ??
    null
  );
}

function shouldShowSourceMarker(block: CanvasBlock, keySourceBlockId: string | null) {
  if (block.type === "asset" && block.asset_url) return true;
  if (block.type === "video" && block.asset_url) return true;
  return block.id === keySourceBlockId;
}

function youtubeEmbedUrl(url: string) {
  try {
    const parsed = new URL(url);
    const host = parsed.hostname.toLowerCase();
    const parts = parsed.pathname.split("/").filter(Boolean);
    const videoId = host.endsWith("youtu.be")
      ? parts[0]
      : parsed.pathname === "/watch"
        ? parsed.searchParams.get("v")
        : parts[0] === "embed"
          ? parts[1]
          : null;
    if (!videoId || !/^[A-Za-z0-9_-]{11}$/.test(videoId)) return null;
    const start = parsed.searchParams.get("t") ?? parsed.searchParams.get("start");
    const params = start ? `?start=${Number.parseInt(start, 10) || 0}` : "";
    return `https://www.youtube-nocookie.com/embed/${videoId}${params}`;
  } catch {
    return null;
  }
}
