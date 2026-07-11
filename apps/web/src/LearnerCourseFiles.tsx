import { useI18n } from "./i18n";
import type { LearnerCourseProfile, UniversityCourse } from "./types";

export function LearnerCourseFiles({
  courses,
  profiles,
  pending,
  onClearMemory,
}: {
  courses: UniversityCourse[];
  profiles: LearnerCourseProfile[];
  pending: boolean;
  onClearMemory: (courseId: string) => Promise<void>;
}) {
  const { t } = useI18n();
  const entries = mergeCourses(courses, profiles);

  return (
    <section className="learner-profile-section" aria-labelledby="learner-files-heading">
      <h2 id="learner-files-heading">{t("profile.files.title")}</h2>
      <p>{t("profile.files.help")}</p>
      <div className="learner-course-files">
        {entries.map(({ course, profile }) => (
          <details key={course.id}>
            <summary>
              <span>
                <strong>{course.title}</strong>
                <small>{t("profile.files.count", { count: profile?.files.length ?? 0 })}</small>
              </span>
            </summary>
            <div className="course-memory-summary">
              <div>
                <strong>{t("profile.memory.course")}</strong>
                <p>{profile?.memory || t("profile.memory.empty")}</p>
              </div>
              {profile?.memory ? (
                <button
                  disabled={pending}
                  type="button"
                  onClick={() => void onClearMemory(course.id)}
                >
                  {t("profile.memory.clearCourse")}
                </button>
              ) : null}
            </div>
            {profile?.files.length ? (
              <div className="learner-file-list">
                {profile.files.map((file) => (
                  <details key={file.path}>
                    <summary>
                      <span>{file.path}</span>
                      <small>{formatBytes(file.size_bytes)}</small>
                    </summary>
                    {file.content ? (
                      <pre>{file.content}</pre>
                    ) : (
                      <p>{t("profile.files.noPreview")}</p>
                    )}
                  </details>
                ))}
              </div>
            ) : (
              <p className="profile-empty-copy">{t("profile.files.empty")}</p>
            )}
          </details>
        ))}
      </div>
    </section>
  );
}

function mergeCourses(courses: UniversityCourse[], profiles: LearnerCourseProfile[]) {
  const known = new Map(courses.map((course) => [course.id, course]));
  for (const profile of profiles) {
    if (!known.has(profile.course_id)) {
      known.set(profile.course_id, {
        id: profile.course_id,
        title: profile.course_id,
        professor: "",
        term: "",
      });
    }
  }
  return Array.from(known.values()).map((course) => ({
    course,
    profile: profiles.find((item) => item.course_id === course.id),
  }));
}

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  return `${(bytes / 1024).toFixed(1)} KB`;
}
