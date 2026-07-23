import { useI18n } from "./i18n";
import type { LearnerCourseProfile, UniversityCourse } from "./types";

export function LearnerCourseFiles({
  courses,
  profiles,
}: {
  courses: UniversityCourse[];
  profiles: LearnerCourseProfile[];
}) {
  const { t } = useI18n();
  const entries = mergeCourses(courses, profiles).filter(
    ({ profile }) => (profile?.files.length ?? 0) > 0,
  );
  if (!entries.length) return null;

  return (
    <section className="learner-profile-section" aria-labelledby="learner-files-heading">
      <div className="profile-section-intro">
        <h2 id="learner-files-heading">{t("profile.files.title")}</h2>
        <p>{t("profile.files.help")}</p>
      </div>
      <div className="profile-section-content">
        <div className="learner-course-files">
          {entries.map(({ course, profile }) => (
            <details key={course.id}>
              <summary>
                <span>
                  <strong>{course.title}</strong>
                  <small>{t("profile.files.count", { count: profile?.files.length ?? 0 })}</small>
                </span>
              </summary>
              <div className="learner-file-list">
                {profile?.files.map((file) => (
                  <details key={file.path}>
                    <summary>
                      <span title={file.path}>{personalFileLabel(file.path)}</span>
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
            </details>
          ))}
        </div>
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

function personalFileLabel(path: string) {
  const match = path.match(
    /^lectures\/([^/]+)\/canvas\/(?:student|components|student-assets)\/(.+)$/,
  );
  return match ? `${match[1]} · ${match[2]}` : path;
}
