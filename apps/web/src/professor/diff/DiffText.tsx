import { lazy, Suspense } from "react";

const RenderedDiffText = lazy(() =>
  import("./RenderedDiffText").then((module) => ({ default: module.RenderedDiffText })),
);

/** Renders canvas Markdown/LaTeX like the learner canvas; shows the source until it loads. */
export function DiffText({ inline = false, text }: { inline?: boolean; text: string }) {
  const Raw = inline ? "span" : "div";
  return (
    <Suspense fallback={<Raw className="diff-text-raw">{text}</Raw>}>
      <RenderedDiffText inline={inline} text={text} />
    </Suspense>
  );
}
