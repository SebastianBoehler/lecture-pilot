import { useI18n } from "./i18n";
import { findProfileCourse, humanizeCourseId } from "./profileCourseDisplay";
import type { LearnerCourseProfile, LearnerFile, UniversityCourse } from "./types";

export function LearnerCourseFiles({
  courses,
  profiles,
}: {
  courses: UniversityCourse[];
  profiles: LearnerCourseProfile[];
}) {
  const { t } = useI18n();
  const entries = mergeCourses(courses, profiles).filter(({ files }) => files.length > 0);
  if (!entries.length) return null;

  return (
    <section className="learner-profile-section" aria-labelledby="learner-files-heading">
      <div className="profile-section-intro">
        <h2 id="learner-files-heading">{t("profile.files.title")}</h2>
        <p>{t("profile.files.help")}</p>
      </div>
      <div className="profile-section-content">
        <div className="learner-course-files">
          {entries.map(({ course, files }) => (
            <details key={course.id}>
              <summary>
                <span>
                  <strong>{course.title}</strong>
                  <small>{t("profile.files.count", { count: files.length })}</small>
                </span>
              </summary>
              <div className="learner-file-list">
                {files.map((file) => (
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
  const entries = new Map<string, { course: UniversityCourse; files: LearnerFile[] }>(
    courses.map((course) => [course.id, { course, files: [] }]),
  );
  for (const profile of profiles) {
    const matchedCourse = findProfileCourse(profile.course_id, courses);
    const key = matchedCourse?.id ?? profile.course_id;
    const entry = entries.get(key) ?? {
      course: matchedCourse ?? {
        id: profile.course_id,
        title: humanizeCourseId(profile.course_id),
        professor: "",
        term: "",
      },
      files: [],
    };
    const knownPaths = new Set(entry.files.map((file) => file.path));
    for (const file of profile.files) {
      if (!knownPaths.has(file.path)) entry.files.push(file);
    }
    entries.set(key, entry);
  }
  return Array.from(entries.values());
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
