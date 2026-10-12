export function youtubeEmbedUrl(url: string) {
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
