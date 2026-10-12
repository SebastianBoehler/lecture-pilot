/** Pure layout helpers for the share slide, kept separate from canvas drawing for tests. */
export type Measure = (text: string, size: number) => number;

export type FittedText = { size: number; lines: string[] };

/** Word-wraps `text` greedily so every line fits `maxWidth` at `size`. */
export function wrapWords(measure: Measure, text: string, size: number, maxWidth: number) {
  const lines: string[] = [];
  let line = "";
  for (const word of text.split(/\s+/).filter(Boolean)) {
    const candidate = line ? `${line} ${word}` : word;
    if (line && measure(candidate, size) > maxWidth) {
      lines.push(line);
      line = word;
    } else {
      line = candidate;
    }
  }
  if (line) lines.push(line);
  return lines;
}

/** Picks the largest size whose wrapped lines stay within `maxLines` and `maxHeight`. */
export function fitTitle(
  measure: Measure,
  text: string,
  options: { maxWidth: number; maxHeight: number; maxLines: number; sizes: number[] },
): FittedText {
  for (const size of options.sizes) {
    const lines = wrapWords(measure, text, size, options.maxWidth);
    if (
      lines.length <= options.maxLines &&
      lines.length * size * LINE_HEIGHT <= options.maxHeight
    ) {
      return { size, lines };
    }
  }
  const size = options.sizes[options.sizes.length - 1];
  const lines = wrapWords(measure, text, size, options.maxWidth);
  if (lines.length <= options.maxLines) return { size, lines };
  const kept = lines.slice(0, options.maxLines);
  kept[kept.length - 1] = ellipsize(measure, kept[kept.length - 1], size, options.maxWidth);
  return { size, lines: kept };
}

/** Breaks a URL (shown without its scheme) at slashes, falling back to characters. */
export function wrapUrl(measure: Measure, url: string, size: number, maxWidth: number) {
  const text = url.replace(/^https?:\/\//, "");
  const segments = text.split(/(?=\/)/);
  const lines: string[] = [];
  let line = "";
  for (const segment of segments) {
    if (measure(line + segment, size) <= maxWidth) {
      line += segment;
      continue;
    }
    if (line) lines.push(line);
    line = "";
    for (const char of segment) {
      if (line && measure(line + char, size) > maxWidth) {
        lines.push(line);
        line = "";
      }
      line += char;
    }
  }
  if (line) lines.push(line);
  return lines;
}

/** The first size whose wrapped link stays within its line limit; null if none fits. */
export function fitUrl(
  measure: Measure,
  url: string,
  maxWidth: number,
  options: { size: number; maxLines: number }[],
): FittedText | null {
  for (const { size, maxLines } of options) {
    const lines = wrapUrl(measure, url, size, maxWidth);
    if (lines.length <= maxLines) return { size, lines };
  }
  return null;
}

function ellipsize(measure: Measure, line: string, size: number, maxWidth: number) {
  let text = line;
  while (text && measure(`${text}…`, size) > maxWidth) text = text.slice(0, -1);
  return `${text.trimEnd()}…`;
}

export const LINE_HEIGHT = 1.12;
