import { createContext, useContext, useState, type ReactNode } from "react";

const Drafts = createContext<Map<string, string> | null>(null);

export function CheckpointDrafts({ children }: { children: ReactNode }) {
  const [drafts] = useState(() => new Map<string, string>());
  return <Drafts.Provider value={drafts}>{children}</Drafts.Provider>;
}

export function useCheckpointAnswer(key: string) {
  const drafts = useContext(Drafts);
  const [answer, setLocalAnswer] = useState(() => drafts?.get(key) ?? "");
  function setAnswer(value: string) {
    if (value) drafts?.set(key, value);
    else drafts?.delete(key);
    setLocalAnswer(value);
  }
  return [answer, setAnswer] as const;
}
