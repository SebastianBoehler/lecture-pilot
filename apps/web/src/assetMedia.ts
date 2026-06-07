export function isPdfAsset(path?: string | null) {
  return Boolean(path?.toLowerCase().split("?")[0].endsWith(".pdf"));
}

export function assetPreviewUrl(url: string, path?: string | null) {
  return isPdfAsset(path ?? url) ? `${url}${url.includes("?") ? "&" : "?"}preview=png` : url;
}
