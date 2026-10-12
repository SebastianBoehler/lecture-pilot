import { createContext, useContext, useState, type ReactNode } from "react";

type DraftStore = { values: Map<string, string>; storageKey?: string };
const Drafts = createContext<DraftStore | null>(null);

export function CheckpointDrafts({
  children,
  storageKey,
}: {
  children: ReactNode;
  storageKey?: string;
}) {
  const [drafts] = useState<DraftStore>(() => {
    let saved: unknown = null;
    try {
      saved = storageKey ? JSON.parse(sessionStorage.getItem(storageKey) ?? "null") : null;
    } catch {
      saved = null;
    }
    const entries = Array.isArray(saved)
      ? (saved.filter(
          (item) =>
            Array.isArray(item) &&
            item.length === 2 &&
            item.every((value) => typeof value === "string") &&
            item[0].includes(":sequence:"),
        ) as [string, string][])
      : [];
    return { values: new Map(entries), storageKey };
  });
  return <Drafts.Provider value={drafts}>{children}</Drafts.Provider>;
}

export function useCheckpointAnswer(key: string) {
  const drafts = useContext(Drafts);
  const [answer, setLocalAnswer] = useState(() => drafts?.values.get(key) ?? "");
  function setAnswer(value: string) {
    if (value) drafts?.values.set(key, value);
    else drafts?.values.delete(key);
    try {
      if (drafts?.storageKey && key.includes(":sequence:"))
        sessionStorage.setItem(
          drafts.storageKey,
          JSON.stringify(
            [...drafts.values].filter(([draftKey]) => draftKey.includes(":sequence:")),
          ),
        );
    } catch {
      /* The current tab still retains the draft when storage is unavailable. */
    }
    setLocalAnswer(value);
  }
  return [answer, setAnswer] as const;
}
