import katex from "katex";
import "katex/dist/katex.min.css";

export function MathText({ highlightedText, text }: { highlightedText: string | null; text: string }) {
  const pieces = splitInlineMath(text);
  return (
    <>
      {pieces.map((piece, index) =>
        piece.math ? (
          <span
            dangerouslySetInnerHTML={{ __html: renderMath(piece.text, false) }}
            key={`${piece.text}-${index}`}
          />
        ) : (
          <TextWithHighlight
            highlightedText={highlightedText}
            key={`${piece.text}-${index}`}
            text={piece.text}
          />
        ),
      )}
    </>
  );
}

export function DisplayMath({ expression }: { expression: string }) {
  return <div dangerouslySetInnerHTML={{ __html: renderMath(expression, true) }} />;
}

function TextWithHighlight({
  highlightedText,
  text,
}: {
  highlightedText: string | null;
  text: string;
}) {
  if (!highlightedText?.trim()) return <span>{text}</span>;
  const ranges = splitByPhrase(text, highlightedText.trim());
  return (
    <span>
      {ranges.map((range, index) =>
        range.highlight ? (
          <mark className="phrase-highlight" key={`${range.text}-${index}`}>
            {range.text}
          </mark>
        ) : (
          <span key={`${range.text}-${index}`}>{range.text}</span>
        ),
      )}
    </span>
  );
}

function splitByPhrase(text: string, phrase: string) {
  const lowerText = text.toLowerCase();
  const lowerPhrase = phrase.toLowerCase();
  const pieces: Array<{ text: string; highlight: boolean }> = [];
  let cursor = 0;
  let matchIndex = lowerText.indexOf(lowerPhrase, cursor);
  while (matchIndex !== -1) {
    if (matchIndex > cursor) pieces.push({ text: text.slice(cursor, matchIndex), highlight: false });
    pieces.push({ text: text.slice(matchIndex, matchIndex + phrase.length), highlight: true });
    cursor = matchIndex + phrase.length;
    matchIndex = lowerText.indexOf(lowerPhrase, cursor);
  }
  if (cursor < text.length) pieces.push({ text: text.slice(cursor), highlight: false });
  return pieces.length ? pieces : [{ text, highlight: false }];
}

function splitInlineMath(text: string) {
  const pieces: Array<{ text: string; math: boolean }> = [];
  let cursor = 0;
  for (const match of text.matchAll(/\$([^$]+)\$|\\\((.*?)\\\)/g)) {
    if (match.index === undefined) continue;
    if (match.index > cursor) pieces.push({ text: text.slice(cursor, match.index), math: false });
    pieces.push({ text: match[1] ?? match[2] ?? "", math: true });
    cursor = match.index + match[0].length;
  }
  if (cursor < text.length) pieces.push({ text: text.slice(cursor), math: false });
  return pieces.length ? pieces : [{ text, math: false }];
}

function renderMath(expression: string, displayMode: boolean) {
  return katex.renderToString(expression, {
    displayMode,
    macros: {
      "\\D": "\\mathcal{D}",
      "\\H": "\\mathcal{H}",
      "\\L": "\\mathcal{L}",
      "\\N": "\\mathbb{N}",
      "\\nicefrac": "\\frac{#1}{#2}",
      "\\x": "\\mathbf{x}",
    },
    output: "html",
    strict: "ignore",
    throwOnError: false,
    trust: false,
  });
}
