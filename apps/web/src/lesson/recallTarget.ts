import type { InkLecture } from "./inkPairingApi";
import type { PublishedCanvasView } from "./publishedCanvasView";

export type RecallTarget = InkLecture & {
  sectionId: string;
  title: string;
  publicationVersion: number;
  blockId?: string;
};

export function getRecallTarget(
  lecture: InkLecture,
  published: PublishedCanvasView | null,
  focusedSectionId: string,
  activeAnchorId: string | null,
): RecallTarget | undefined {
  if (!published) return;
  const sections = published.document.sections;
  const section =
    sections.find(
      ({ id, blocks }) =>
        id === activeAnchorId || blocks.some((block) => block.id === activeAnchorId),
    ) ?? sections.find(({ id }) => id === focusedSectionId);
  if (!section) return;
  const teaching = section.blocks.find(
    ({ type, id }) => id && !["prediction", "checkpoint", "quiz"].includes(type),
  );
  return {
    ...lecture,
    sectionId: section.id,
    title: section.title,
    publicationVersion: published.publication_version,
    blockId: teaching?.id ?? undefined,
  };
}
