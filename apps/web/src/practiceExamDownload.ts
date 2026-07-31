import { downloadPracticeExamPdf } from "./practiceExamApi";
import type { LoginSession } from "./types";

export async function savePracticeExamPdf(courseId: string, examId: string, session: LoginSession) {
  const blob = await downloadPracticeExamPdf(courseId, examId, session);
  const url = URL.createObjectURL(blob);
  try {
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `practice-exam-${examId.slice(0, 8)}.pdf`;
    anchor.click();
  } finally {
    URL.revokeObjectURL(url);
  }
}
