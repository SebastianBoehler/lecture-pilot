import { downloadPracticeExamPdf, downloadPracticeExamSolutionPdf } from "./practiceExamApi";
import type { LoginSession } from "./types";

export async function savePracticeExamPdf(courseId: string, examId: string, session: LoginSession) {
  const blob = await downloadPracticeExamPdf(courseId, examId, session);
  savePdfBlob(blob, `practice-exam-${examId.slice(0, 8)}.pdf`);
}

export async function savePracticeExamSolutionPdf(
  courseId: string,
  examId: string,
  session: LoginSession,
) {
  const blob = await downloadPracticeExamSolutionPdf(courseId, examId, session);
  savePdfBlob(blob, `practice-exam-${examId.slice(0, 8)}-solutions.pdf`);
}

function savePdfBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  try {
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    anchor.click();
  } finally {
    URL.revokeObjectURL(url);
  }
}
