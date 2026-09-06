import type { CanvasDocument } from "./types";
import type { LanguageVariant, TeachingText } from "./canvasLanguageApi";

export function teachingLanguageOverlay(
  document: CanvasDocument,
  variant: LanguageVariant,
  originals: TeachingText[],
): CanvasDocument {
  const changes = new Map(variant.texts.map((text) => [text.key, text.text]));
  const base = new Map(originals.map((text) => [text.key, text.text]));
  function translate(key: string, text: string | null | undefined) {
    return text === base.get(key) ? (changes.get(key) ?? text) : text;
  }
  return {
    ...document,
    title: translate("title", document.title)!,
    sections: document.sections.map((section) => ({
      ...section,
      title: translate(`section:${section.id}`, section.title)!,
      blocks: section.blocks.map((block) => {
        if (!["paragraph", "list", "callout", "asset", "video", "table"].includes(block.type))
          return block;
        const prefix = `block:${section.id}:${block.id}`;
        return {
          ...block,
          text: translate(`${prefix}:text`, block.text),
          caption: translate(`${prefix}:caption`, block.caption),
          items: block.items.map((text, index) => translate(`${prefix}:item:${index}`, text)!),
        };
      }),
    })),
  };
}
