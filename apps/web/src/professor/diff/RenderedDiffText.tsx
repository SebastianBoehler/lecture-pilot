import { MathText } from "../../canvas/MathText";

/** Canvas Markdown and LaTeX rendering for diff text; loaded lazily with the KaTeX chunk. */
export function RenderedDiffText({ inline, text }: { inline: boolean; text: string }) {
  return (
    <MathText
      allowLinks={false}
      highlightedText={null}
      mode={inline ? "inline" : "block"}
      text={text}
    />
  );
}
