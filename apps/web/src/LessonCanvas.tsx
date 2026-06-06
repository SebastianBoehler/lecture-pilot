import { useEffect } from "react";
import katex from "katex";
import "katex/dist/katex.min.css";

import { apiUrl } from "./api";
import type { CanvasBlock, CanvasDocument, CanvasSection, DocumentAnchorId, Lecture } from "./types";

export function LessonCanvas({
  canvasDocument,
  lecture,
  focusedSectionId,
  highlightedBlockId,
  activeAnchorId,
}: {
  canvasDocument: CanvasDocument;
  lecture: Lecture;
  focusedSectionId: string;
  highlightedBlockId: string | null;
  activeAnchorId: DocumentAnchorId | null;
}) {
  useEffect(() => {
    const section = document.getElementById(focusedSectionId);
    if (typeof section?.scrollIntoView === "function") {
      section.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, [focusedSectionId]);

  useEffect(() => {
    const block = highlightedBlockId ? document.getElementById(highlightedBlockId) : null;
    if (typeof block?.scrollIntoView === "function") {
      block.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, [highlightedBlockId]);

  function isActive(id: DocumentAnchorId) {
    return activeAnchorId ? activeAnchorId === id : focusedSectionId === id;
  }

  return (
    <article className="canvas">
      <p className="section-label">Lecture {lecture.number}</p>
      <h1>{canvasDocument.title}</h1>
      <p className="lead">
        A study document for probabilities, Bayes' rule, Naive Bayes classification, and
        risk-aware decisions.
      </p>

      {canvasDocument.sections.map((section) =>
        renderSection({
          section,
          isFocused: isActive(section.id),
          highlightedBlockId,
        }),
      )}
    </article>
  );
}

function renderSection({
  section,
  isFocused,
  highlightedBlockId,
}: {
  section: CanvasSection;
  isFocused: boolean;
  highlightedBlockId: string | null;
}) {
  return (
    <section
      aria-current={isFocused ? "true" : undefined}
      aria-labelledby={`${section.id}-heading`}
      className={isFocused ? "canvas-section is-focused" : "canvas-section"}
      id={section.id}
      key={section.id}
    >
      {isFocused ? <span className="focus-chip">In focus</span> : null}
      {section.source_ref ? <p className="section-label">{section.source_ref}</p> : null}
      <h2 id={`${section.id}-heading`}>{section.title}</h2>
      {section.blocks.map((block) => renderBlock(block, highlightedBlockId === block.id))}
    </section>
  );
}

function renderBlock(block: CanvasBlock, isHighlighted: boolean) {
  const className = isHighlighted ? "canvas-block is-highlighted" : "canvas-block";
  if (block.type === "list") {
    return (
      <ul className={`${className} canvas-list`} id={block.id} key={block.id}>
        {block.items.map((item) => (
          <li key={item}>
            <MathText text={item} />
          </li>
        ))}
      </ul>
    );
  }

  if (block.type === "asset" && block.asset_url) {
    return (
      <figure className={`${className} canvas-asset`} id={block.id} key={block.id}>
        <img alt={block.caption ?? "Course figure"} src={apiUrl(block.asset_url)} />
        {block.caption ? <figcaption>{block.caption}</figcaption> : null}
      </figure>
    );
  }

  if (block.type === "callout") {
    return (
      <aside className={`${className} canvas-callout`} id={block.id} key={block.id}>
        <MathText text={block.text ?? ""} />
      </aside>
    );
  }

  if (block.type === "math" && block.text) {
    return (
      <div
        className={`${className} canvas-math`}
        dangerouslySetInnerHTML={{ __html: renderMath(block.text, true) }}
        id={block.id}
        key={block.id}
      />
    );
  }

  return (
    <p className={className} id={block.id} key={block.id}>
      <MathText text={block.text ?? ""} />
    </p>
  );
}

function MathText({ text }: { text: string }) {
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
          <span key={`${piece.text}-${index}`}>{piece.text}</span>
        ),
      )}
    </>
  );
}

function splitInlineMath(text: string) {
  const pieces: Array<{ text: string; math: boolean }> = [];
  let cursor = 0;
  for (const match of text.matchAll(/\$([^$]+)\$|\\\((.*?)\\\)/g)) {
    if (match.index === undefined) {
      continue;
    }
    if (match.index > cursor) {
      pieces.push({ text: text.slice(cursor, match.index), math: false });
    }
    pieces.push({ text: match[1] ?? match[2] ?? "", math: true });
    cursor = match.index + match[0].length;
  }
  if (cursor < text.length) {
    pieces.push({ text: text.slice(cursor), math: false });
  }
  return pieces.length ? pieces : [{ text, math: false }];
}

function renderMath(expression: string, displayMode: boolean) {
  return katex.renderToString(expression, {
    displayMode,
    macros: {
      "\\D": "\\mathcal{D}",
      "\\N": "\\mathbb{N}",
      "\\x": "\\mathbf{x}",
    },
    output: "html",
    strict: "ignore",
    throwOnError: false,
    trust: false,
  });
}
