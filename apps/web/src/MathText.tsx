import katex from "katex";
import "katex/dist/katex.min.css";

export function MathText({ highlightedText, text }: { highlightedText: string | null; text: string }) {
  const pieces = splitInlineMath(text);
  return (
    <>
      {pieces.map((piece, index) =>
        piece.math ? (
          <span
            className={piece.displayMode ? "math-display" : undefined}
            dangerouslySetInnerHTML={{ __html: renderMath(piece.text, piece.displayMode) }}
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
  if (!highlightedText?.trim()) return <MarkdownInline text={text} />;
  const ranges = splitByPhrase(text, highlightedText.trim());
  return (
    <span>
      {ranges.map((range, index) =>
        range.highlight ? (
          <mark className="phrase-highlight" key={`${range.text}-${index}`}>
            <MarkdownInline text={range.text} />
          </mark>
        ) : (
          <MarkdownInline key={`${range.text}-${index}`} text={range.text} />
        ),
      )}
    </span>
  );
}

function MarkdownInline({ text }: { text: string }) {
  const pieces = splitMarkdownInline(text);
  return (
    <>
      {pieces.map((piece, index) => {
        const key = `${piece.text}-${index}`;
        if (piece.kind === "strong") return <strong key={key}><LooseInlineMath text={piece.text} /></strong>;
        if (piece.kind === "code") return <code key={key}>{piece.text}</code>;
        return <LooseInlineMath key={key} text={piece.text} />;
      })}
    </>
  );
}

function LooseInlineMath({ text }: { text: string }) {
  const pieces = splitLooseInlineMath(text);
  return (
    <>
      {pieces.map((piece, index) =>
        piece.math ? (
          <span
            dangerouslySetInnerHTML={{ __html: renderMath(piece.text, false) }}
            key={`${piece.text}-${index}`}
          />
        ) : (
          <span key={`${piece.text}-${index}`}>{piece.text}</span>
        ),
      )}
    </>
  );
}

function splitMarkdownInline(text: string) {
  const pieces: Array<{ kind: "text" | "strong" | "code"; text: string }> = [];
  let cursor = 0;
  for (const match of text.matchAll(/`([^`]+)`|\*\*([^*]+)\*\*/g)) {
    if (match.index === undefined) continue;
    if (match.index > cursor) pieces.push({ kind: "text", text: text.slice(cursor, match.index) });
    pieces.push({ kind: match[1] ? "code" : "strong", text: match[1] ?? match[2] ?? "" });
    cursor = match.index + match[0].length;
  }
  if (cursor < text.length) pieces.push({ kind: "text", text: text.slice(cursor) });
  return pieces.length ? pieces : [{ kind: "text", text }];
}

function splitLooseInlineMath(text: string) {
  const pieces: Array<{ text: string; math: boolean }> = [];
  let cursor = 0;
  for (const match of text.matchAll(/\\[a-zA-Z]+(?:\s*[_^](?:\{[^{}]+\}|[a-zA-Z0-9]+))*/g)) {
    if (match.index === undefined) continue;
    if (match.index > cursor) pieces.push({ text: text.slice(cursor, match.index), math: false });
    pieces.push({ text: match[0], math: true });
    cursor = match.index + match[0].length;
  }
  if (cursor < text.length) pieces.push({ text: text.slice(cursor), math: false });
  return pieces.length ? pieces : [{ text, math: false }];
}

function splitByPhrase(text: string, phrase: string) {
  const target = highlightTarget(text, phrase);
  if (!target) return [{ text, highlight: false }];
  const lowerText = text.toLowerCase();
  const lowerPhrase = target.toLowerCase();
  const pieces: Array<{ text: string; highlight: boolean }> = [];
  let cursor = 0;
  let matchIndex = lowerText.indexOf(lowerPhrase, cursor);
  while (matchIndex !== -1) {
    if (matchIndex > cursor) pieces.push({ text: text.slice(cursor, matchIndex), highlight: false });
    pieces.push({ text: text.slice(matchIndex, matchIndex + target.length), highlight: true });
    cursor = matchIndex + target.length;
    matchIndex = lowerText.indexOf(lowerPhrase, cursor);
  }
  if (cursor < text.length) pieces.push({ text: text.slice(cursor), highlight: false });
  return pieces.length ? pieces : [{ text, highlight: false }];
}

function highlightTarget(text: string, phrase: string) {
  const lowerText = text.toLowerCase();
  if (lowerText.includes(phrase.toLowerCase())) return phrase;
  let candidate = phrase.replace(/\.\.\.$/, "").trim();
  while (candidate.length >= 14) {
    if (lowerText.includes(candidate.toLowerCase())) return candidate;
    const shortened = candidate.replace(/\s+\S+$/, "").trim();
    if (shortened === candidate) break;
    candidate = shortened;
  }
  return null;
}

function splitInlineMath(text: string) {
  const pieces: Array<{ text: string; math: boolean; displayMode: boolean }> = [];
  let cursor = 0;
  for (const match of text.matchAll(/\\{1,2}\[([\s\S]*?)\\{1,2}\]|\$\$([\s\S]*?)\$\$|\$([^$]+)\$|\\{1,2}\((.*?)\\{1,2}\)/g)) {
    if (match.index === undefined) continue;
    if (match.index > cursor) {
      pieces.push({ displayMode: false, text: text.slice(cursor, match.index), math: false });
    }
    pieces.push({
      displayMode: match[1] !== undefined || match[2] !== undefined,
      math: true,
      text: match[1] ?? match[2] ?? match[3] ?? match[4] ?? "",
    });
    cursor = match.index + match[0].length;
  }
  if (cursor < text.length) pieces.push({ displayMode: false, text: text.slice(cursor), math: false });
  return pieces.length ? pieces : [{ displayMode: false, text, math: false }];
}

function renderMath(expression: string, displayMode: boolean) {
  return katex.renderToString(normalizeMathExpression(expression), {
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

function normalizeMathExpression(expression: string) {
  return expression.replaceAll("...", "\\dots");
}
