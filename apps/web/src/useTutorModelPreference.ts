import { useEffect, useState } from "react";

import {
  readStoredTutorModelPreference,
  type TutorModelPreference,
  writeStoredTutorModelPreference,
} from "./tutorModels";

export function useTutorModelPreference() {
  const [preference, setPreference] = useState<TutorModelPreference>(() =>
    readStoredTutorModelPreference(),
  );

  useEffect(() => {
    writeStoredTutorModelPreference(preference);
  }, [preference]);

  return [preference, setPreference] as const;
}
