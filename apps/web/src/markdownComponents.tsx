import { Children, isValidElement, type ComponentProps, type ReactNode, useState } from "react";
import type { Components } from "react-markdown";

const inlineComponents: Components = {
  a: SafeLink,
  p: ({ children }) => <>{children}</>,
};

const blockComponents: Components = {
  a: SafeLink,
  pre: MarkdownCodeBlock,
};

const inlineComponentsWithoutLinks: Components = {
  a: TextOnlyLink,
  p: ({ children }) => <>{children}</>,
};

const blockComponentsWithoutLinks: Components = {
  a: TextOnlyLink,
  pre: MarkdownCodeBlock,
};

export function markdownComponents(mode: "inline" | "block", allowLinks: boolean) {
  if (mode === "inline") {
    return allowLinks ? inlineComponents : inlineComponentsWithoutLinks;
  }
  return allowLinks ? blockComponents : blockComponentsWithoutLinks;
}

function TextOnlyLink({ children }: ComponentProps<"a">) {
  return <>{children}</>;
}

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

function MarkdownCodeBlock({ children }: ComponentProps<"pre">) {
  const [copyState, setCopyState] = useState<"idle" | "copied" | "failed">("idle");
  const language = codeLanguage(children);
  const code = nodeText(children).replace(/\n$/, "");

  async function copyCode() {
    try {
      await navigator.clipboard.writeText(code);
      setCopyState("copied");
      window.setTimeout(() => setCopyState("idle"), 1600);
    } catch {
      setCopyState("failed");
    }
  }

  return (
    <div className="markdown-code-block">
      <div className="markdown-code-toolbar">
        <span>{language || "code"}</span>
        <button type="button" onClick={() => void copyCode()}>
          {copyState === "copied" ? "Copied" : copyState === "failed" ? "Copy failed" : "Copy"}
        </button>
      </div>
      <pre>{children}</pre>
    </div>
  );
}

function codeLanguage(children: ReactNode) {
  const child = Children.toArray(children).find(isValidElement);
  if (!child || typeof child.props !== "object" || child.props === null) return "";
  const className = "className" in child.props ? child.props.className : "";
  const match = typeof className === "string" ? className.match(/(?:^|\s)language-([\w-]+)/) : null;
  return match?.[1] ?? "";
}

function nodeText(node: ReactNode): string {
  if (typeof node === "string" || typeof node === "number") return String(node);
  if (Array.isArray(node)) return node.map(nodeText).join("");
  if (!isValidElement(node)) return "";
  return nodeText((node.props as { children?: ReactNode }).children);
}
