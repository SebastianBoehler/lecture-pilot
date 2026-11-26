import { useEffect, useState } from "react";
import { PairedInkDialog } from "./RecallDialog";
import { inkPairCode, type InkLecture } from "./inkPairingApi";

export function LessonInkPair({ lecture }: { lecture: InkLecture }) {
  const [code, setCode] = useState(() => inkPairCode(window.location.hash));
  useEffect(() => {
    const update = () => setCode(inkPairCode(window.location.hash));
    window.addEventListener("hashchange", update);
    return () => window.removeEventListener("hashchange", update);
  }, []);

  function close() {
    window.history.replaceState(
      window.history.state,
      "",
      window.location.pathname + window.location.search,
    );
    setCode(null);
  }

  return code ? <PairedInkDialog key={code} lecture={lecture} code={code} onClose={close} /> : null;
}
