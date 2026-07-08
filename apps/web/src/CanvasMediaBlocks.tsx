import type { ReactNode } from "react";

import { apiUrl } from "./api";
import { assetPreviewUrl } from "./assetMedia";
import {
  AuthenticatedAssetLink,
  AuthenticatedImage,
  AuthenticatedVideo,
} from "./AuthenticatedAsset";
import type { CanvasBlock, LoginSession } from "./types";
import { youtubeEmbedUrl } from "./youtubeEmbedUrl";

type MediaBlockOptions = {
  className: string;
  session: LoginSession;
  sourceMarker: ReactNode;
};

export function renderAssetBlock(block: CanvasBlock, options: MediaBlockOptions) {
  const assetUrl = block.asset_url;
  if (!assetUrl) return null;
  const url = assetPreviewUrl(assetUrl, block.asset_path ?? assetUrl);
  const caption = block.caption ?? "Course figure";
  return (
    <figure className={`${options.className} canvas-asset`} id={block.id} key={block.id}>
      <AuthenticatedImage alt={caption} session={options.session} src={url} />
      <figcaption>
        {block.caption}
        {options.sourceMarker}
      </figcaption>
    </figure>
  );
}

export function renderVideoBlock(block: CanvasBlock, options: MediaBlockOptions) {
  const assetUrl = block.asset_url;
  if (!assetUrl) return null;
  const embedUrl = youtubeEmbedUrl(assetUrl);
  const nativeVideo = /\.(mp4|webm|mov)(?:$|\?)/i.test(assetUrl);
  const title = block.caption ?? "YouTube video";
  return (
    <figure className={`${options.className} canvas-video`} id={block.id} key={block.id}>
      <div className="canvas-video-frame">
        {embedUrl ? (
          <iframe
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowFullScreen
            src={embedUrl}
            title={title}
          />
        ) : nativeVideo ? (
          <AuthenticatedVideo session={options.session} src={assetUrl} title={title} />
        ) : (
          <AuthenticatedAssetLink session={options.session} src={apiUrl(assetUrl)}>
            Open video
          </AuthenticatedAssetLink>
        )}
      </div>
      <figcaption>
        <strong>{title}</strong>
        {block.text ? <span>{block.text}</span> : null}
        {options.sourceMarker}
      </figcaption>
    </figure>
  );
}
