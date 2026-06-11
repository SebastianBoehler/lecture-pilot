import ReactMarkdown, { type Components } from "react-markdown";
import type { ComponentProps } from "react";
import { useLayoutEffect, useRef } from "react";
import rehypeKatex from "rehype-katex";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import katex from "katex";
import "katex/dist/katex.min.css";

type MathTextMode = "inline" | "block";

const katexOptions = {
  macros: {
    "\\D": "\\mathcal{D}",
    "\\H": "\\mathcal{H}",
    "\\L": "\\mathcal{L}",
    "\\N": "\\mathbb{N}",
    "\\nicefrac": "\\frac{#1}{#2}",
    "\\x": "\\mathbf{x}",
  },
  strict: "ignore" as const,
  throwOnError: false,
  trust: false,
};

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
    ? (
      highlightTarget(plainMarkdownText(markdown), plainMarkdownText(highlightedMarkdown))
      ?? highlightTarget(markdown, highlightedMarkdown)
      ?? leadingTextBeforeMath(highlightedMarkdown)
    )
    : null;
  return <MarkdownRenderer highlightedText={target} mode={mode} text={markdown} />;
}

export function DisplayMath({ expression }: { expression: string }) {
  return (
    <div
      dangerouslySetInnerHTML={{ __html: renderMath(expression, true) }}
    />
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

function SafeLink({
  children,
  href,
}: ComponentProps<"a">) {
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

function textNode(value: string): MarkdownNode {
  return { type: "text", value };
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

function looseLatexPlugin() {
  return (tree: unknown) => {
    splitLooseLatexText(tree as MarkdownNode);
    return tree;
  };
}

function splitLooseLatexText(node: MarkdownNode) {
  if (!node || blockedMarkdownNode(node) || !Array.isArray(node.children)) return;
  const next = [];
  for (const child of node.children) {
    if (child.type === "text" && typeof child.value === "string") {
      next.push(...looseLatexPieces(child.value));
    } else {
      splitLooseLatexText(child);
      next.push(child);
    }
  }
  node.children = next;
}

function looseLatexPieces(value: string): MarkdownNode[] {
  const pieces: MarkdownNode[] = [];
  let cursor = 0;
  for (const match of value.matchAll(/\\+[a-zA-Z]+(?:\s*[_^](?:\{[^{}]+\}|[a-zA-Z0-9]+))*/g)) {
    if (match.index === undefined) continue;
    if (match.index > cursor) pieces.push(textNode(value.slice(cursor, match.index)));
    pieces.push(inlineMathNode(normalizeLooseLatexCommand(match[0])));
    cursor = match.index + match[0].length;
  }
  if (cursor < value.length) pieces.push(textNode(value.slice(cursor)));
  return pieces.length ? pieces : [textNode(value)];
}

function blockedMarkdownNode(node: MarkdownNode) {
  return ["code", "inlineCode", "math", "inlineMath"].includes(String(node.type || ""));
}

function inlineMathNode(value: string): MarkdownNode {
  return {
    type: "inlineMath",
    value,
    data: {
      hName: "code",
      hProperties: { className: ["language-math", "math-inline"] },
      hChildren: [textNode(value)],
    },
  };
}

function normalizeLooseLatexCommand(value: string) {
  return value.replace(/^\\+/, "\\");
}

function renderMath(expression: string, displayMode: boolean) {
  return katex.renderToString(normalizeMathExpression(expression), {
    ...katexOptions,
    displayMode,
    output: "html",
  });
}

function normalizeMathExpression(expression: string) {
  return expression.replaceAll("...", "\\dots");
}

type MarkdownNode = {
  type?: string;
  tagName?: string;
  value?: string;
  properties?: Record<string, unknown>;
  data?: Record<string, unknown>;
  children?: MarkdownNode[];
};
