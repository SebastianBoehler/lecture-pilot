export type WorkspaceResource = {
  id: string;
  kind: "canvas" | "source" | "asset" | "video" | "memory";
  label: string;
  path: string;
  sectionId?: string | null;
  blockId?: string | null;
  displayPath?: string | null;
  detail?: string | null;
  url?: string | null;
};
