import ReactMarkdown, { type Components } from "react-markdown";
import type { ComponentProps } from "react";
import { useLayoutEffect, useRef } from "react";
import rehypeKatex from "rehype-katex";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import "katex/dist/katex.min.css";
import "./math-text.css";

import { katexOptions } from "./courseLatexMacros";
import { delimitedMathIsRenderable, segmentDisplayMath, tryRenderDisplayMath } from "./displayMath";
import { looseLatexPlugin } from "./looseLatex";

type MathTextMode = "inline" | "block";

export function MathText({
  highlightedText,
  mode = "inline",
  text,
}: {
  highlightedText: string | null;
  mode?: MathTextMode;
  text: string;
}) {
  const markdown = normalizeMarkdownMath(text);
  const highlightedMarkdown = highlightedText?.trim()
    ? normalizeMarkdownMath(highlightedText.trim()).trim()
    : null;
  const target = highlightedMarkdown
    ? (highlightTarget(plainMarkdownText(markdown), plainMarkdownText(highlightedMarkdown)) ??
      highlightTarget(markdown, highlightedMarkdown) ??
      leadingTextBeforeMath(highlightedMarkdown))
    : null;
  return <MarkdownRenderer highlightedText={target} mode={mode} text={markdown} />;
}

export function DisplayMath({ expression }: { expression: string }) {
  if (hasDelimitedMath(expression)) {
    if (!delimitedMathIsRenderable(expression)) {
      return <MathRenderFallback expression={expression} />;
    }
    return <MathText highlightedText={null} mode="block" text={expression} />;
  }
  const segments = segmentDisplayMath(expression);
  if (segments.some(({ kind }) => kind === "prose")) {
    return (
      <div>
        {segments.map((segment, index) =>
          segment.kind === "math" ? (
            <RenderedDisplayMath expression={segment.value} key={index} />
          ) : (
            <MathText highlightedText={null} key={index} mode="block" text={segment.value} />
          ),
        )}
      </div>
    );
  }
  return <RenderedDisplayMath expression={expression} />;
}

function RenderedDisplayMath({ expression }: { expression: string }) {
  const html = tryRenderDisplayMath(expression);
  if (!html) return <MathRenderFallback expression={expression} />;
  return <div dangerouslySetInnerHTML={{ __html: html }} />;
}

function MathRenderFallback({ expression }: { expression: string }) {
  return (
    <div aria-label="Formula could not be rendered" className="math-render-fallback" role="note">
      <strong>Formula could not be rendered</strong>
      <pre>
        <code>{expression.trim()}</code>
      </pre>
    </div>
  );
}

function MarkdownRenderer({
  highlightedText,
  mode,
  text,
}: {
  highlightedText?: string | null;
  mode: MathTextMode;
  text: string;
}) {
  const ref = useRef<HTMLDivElement & HTMLSpanElement>(null);
  useLayoutEffect(() => {
    if (ref.current && highlightedText) {
      applyDomHighlight(ref.current, highlightedText);
    }
  }, [highlightedText, text]);
  const content = (
    <ReactMarkdown
      components={mode === "inline" ? inlineComponents : blockComponents}
      rehypePlugins={[[rehypeKatex, katexOptions]]}
      remarkPlugins={[remarkGfm, remarkMath, looseLatexPlugin]}
    >
      {text}
    </ReactMarkdown>
  );
  return mode === "inline" ? <span ref={ref}>{content}</span> : <div ref={ref}>{content}</div>;
}

const inlineComponents: Components = {
  a: SafeLink,
  p: ({ children }) => <>{children}</>,
};

const blockComponents: Components = {
  a: SafeLink,
};

function SafeLink({ children, href }: ComponentProps<"a">) {
  const target = safeHref(href);
  if (!target) return <>{children}</>;
  return (
    <a href={target} rel="noreferrer" target="_blank">
      {children}
    </a>
  );
}

function safeHref(href: string | undefined) {
  if (!href) return "";
  return /^(https?:|mailto:|\/)/.test(href) ? href : "";
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

function applyDomHighlight(root: HTMLElement, phrase: string) {
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
    acceptNode(node) {
      if (!node.nodeValue?.toLowerCase().includes(phrase.toLowerCase())) {
        return NodeFilter.FILTER_REJECT;
      }
      return isHighlightBlocked(node.parentElement)
        ? NodeFilter.FILTER_REJECT
        : NodeFilter.FILTER_ACCEPT;
    },
  });
  const nodes: Text[] = [];
  while (true) {
    const node = walker.nextNode();
    if (!node) break;
    nodes.push(node as Text);
  }
  for (const node of nodes) {
    replaceTextWithHighlight(node, phrase);
  }
}

function replaceTextWithHighlight(node: Text, phrase: string) {
  const value = node.nodeValue ?? "";
  const lowerValue = value.toLowerCase();
  const lowerPhrase = phrase.toLowerCase();
  let cursor = 0;
  let matchIndex = lowerValue.indexOf(lowerPhrase, cursor);
  if (matchIndex === -1) return;
  const fragment = document.createDocumentFragment();
  while (matchIndex !== -1) {
    if (matchIndex > cursor) fragment.append(value.slice(cursor, matchIndex));
    const mark = document.createElement("mark");
    mark.className = "phrase-highlight";
    mark.textContent = value.slice(matchIndex, matchIndex + phrase.length);
    fragment.append(mark);
    cursor = matchIndex + phrase.length;
    matchIndex = lowerValue.indexOf(lowerPhrase, cursor);
  }
  if (cursor < value.length) fragment.append(value.slice(cursor));
  node.replaceWith(fragment);
}

function isHighlightBlocked(element: HTMLElement | null) {
  for (let current = element; current; current = current.parentElement) {
    if (["CODE", "PRE", "SCRIPT", "STYLE"].includes(current.tagName)) return true;
    if (current.classList.contains("katex")) return true;
  }
  return false;
}

function normalizeMarkdownMath(value: string) {
  return value
    .replace(/\\{1,2}\[([\s\S]*?)\\{1,2}\]/g, (_, formula: string) => `\n$$\n${formula}\n$$\n`)
    .replace(/\\{1,2}\(([\s\S]*?)\\{1,2}\)/g, (_, formula: string) => `$${formula}$`);
}

function plainMarkdownText(value: string) {
  return value
    .replace(/\$\$[\s\S]*?\$\$/g, " ")
    .replace(/\$[^$\n]+\$/g, " ")
    .replace(/\\+[a-zA-Z]+(?:\s*[_^](?:\{[^{}]+\}|[a-zA-Z0-9]+))*/g, " ")
    .replace(/[`*_~#[\]()]/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

function leadingTextBeforeMath(value: string) {
  const text = value.split(/\\+[a-zA-Z]+|\$|\n\$\$/)[0]?.trim();
  return text && text.length >= 4 ? text : null;
}

function hasDelimitedMath(expression: string) {
  return /\$\$[\s\S]+?\$\$|\$[^$\n]+\$|\\{1,2}\[[\s\S]+?\\{1,2}\]|\\{1,2}\([\s\S]*?\\{1,2}\)/.test(
    expression,
  );
}
