import type { CourseSetup } from "./professorBuilderState";
import type { LectureScheduleItem, YoutubeVideoCandidate } from "./types";

export type YoutubeCandidateGroup = {
  query: string;
  videos: YoutubeVideoCandidate[];
};

export function youtubeSuggestionQueries(setup: CourseSetup, lectureSchedule: LectureScheduleItem[]) {
  const course = setup.courseTitle.trim();
  const lectureFocus = setup.target === "single-lecture"
    ? setup.lectureTitle.trim()
    : lectureSchedule.slice(0, 3).map((lecture) => lecture.title.trim()).filter(Boolean).join(" ");
  return uniqueQueries([
    [course, lectureFocus, "lecture"].filter(Boolean).join(" "),
    [course, "Universität Tübingen", "machine learning"].filter(Boolean).join(" "),
    [lectureFocus || course, "machine learning explained"].filter(Boolean).join(" "),
  ]).slice(0, 3);
}

export function flattenVideoGroups(groups: YoutubeCandidateGroup[]) {
  const seen = new Set<string>();
  const videos: YoutubeVideoCandidate[] = [];
  for (const group of groups) {
    for (const video of group.videos) {
      if (seen.has(video.video_id)) continue;
      seen.add(video.video_id);
      videos.push(video);
    }
  }
  return videos;
}

function uniqueQueries(queries: string[]) {
  const seen = new Set<string>();
  return queries.filter((query) => {
    const normalized = query.replace(/\s+/g, " ").trim();
    const key = normalized.toLowerCase();
    if (key.length < 4 || seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}
