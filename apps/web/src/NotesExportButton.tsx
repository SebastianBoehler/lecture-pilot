import { FileDown } from "lucide-react";
import { useState } from "react";

import { useI18n } from "./i18n";
import { downloadLectureNotes } from "./studyApi";
import type { LearnerWorkspaceMode, LoginSession } from "./types";

export function NotesExportButton({
  courseId,
  lectureId,
  mode,
  session,
}: {
  courseId: string;
  lectureId: string;
  mode: LearnerWorkspaceMode;
  session: LoginSession;
}) {
  const { t } = useI18n();
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function exportNotes() {
    setExporting(true);
    setError(null);
    try {
      await downloadLectureNotes(courseId, lectureId, session, mode);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : t("notes.exportError"));
    } finally {
      setExporting(false);
    }
  }

  return (
    <div className="notes-export">
      <p>{t("notes.exportHelp")}</p>
      <button disabled={exporting} type="button" onClick={() => void exportNotes()}>
        <FileDown aria-hidden="true" size={15} />
        {exporting ? t("notes.exporting") : t("notes.export")}
      </button>
      {error ? (
        <p className="form-error" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}
