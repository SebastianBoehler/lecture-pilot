import { runBoundedTasks } from "./boundedTaskPool";
import { getSourceBundle, uploadCourseMaterial } from "./professorApi";
import { isSkippableUploadError, uploadDestination } from "./professorUpload";
import type { LoginSession, SourceBundleManifest } from "./types";

const MATERIAL_UPLOAD_CONCURRENCY = 4;

type UploadResult = Awaited<ReturnType<typeof uploadCourseMaterial>>;

export type ProfessorMaterialUploadResult = {
  bundle: SourceBundleManifest | null;
  error: Error | null;
  ignored: string[];
  mutationUncertain: boolean;
  uploaded: UploadResult[];
};

export async function uploadProfessorMaterials({
  courseId,
  files,
  session,
}: {
  courseId: string;
  files: File[];
  session: LoginSession;
}): Promise<ProfessorMaterialUploadResult> {
  const outcomes = new Array<{ ignored?: string; uploaded?: UploadResult }>(files.length);
  let uploadError: Error | null = null;
  let mutationUncertain = false;
  try {
    await runBoundedTasks(files, MATERIAL_UPLOAD_CONCURRENCY, async (file, index) => {
      const path = uploadDestination(file);
      try {
        outcomes[index] = {
          uploaded: await uploadCourseMaterial({
            courseId,
            path,
            file,
            refreshIndex: false,
            session,
          }),
        };
      } catch (error) {
        if (isSkippableUploadError(error)) {
          outcomes[index] = { ignored: path };
          return;
        }
        mutationUncertain = true;
        const message = error instanceof Error ? error.message : String(error);
        throw new Error(`${path}: ${message}`);
      }
    });
  } catch (error) {
    uploadError = error instanceof Error ? error : new Error(String(error));
  }

  let bundle: SourceBundleManifest | null = null;
  try {
    bundle = await getSourceBundle(courseId, session);
  } catch (error) {
    const refreshError = error instanceof Error ? error : new Error(String(error));
    uploadError = uploadError
      ? new Error(
          `${uploadError.message} Source bundle refresh also failed: ${refreshError.message}`,
        )
      : refreshError;
  }
  return {
    bundle,
    error: uploadError,
    ignored: outcomes.flatMap((outcome) => (outcome?.ignored ? [outcome.ignored] : [])),
    mutationUncertain,
    uploaded: outcomes.flatMap((outcome) => (outcome?.uploaded ? [outcome.uploaded] : [])),
  };
}
