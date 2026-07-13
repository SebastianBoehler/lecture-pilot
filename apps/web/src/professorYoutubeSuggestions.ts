import type { CourseSetup } from "./professorBuilderState";
import type { Lecture, YoutubeVideoCandidate } from "./types";

export type YoutubeCandidateGroup = {
  query: string;
  videos: YoutubeVideoCandidate[];
};

export function youtubeSuggestionQueries(setup: CourseSetup, lecture?: Lecture) {
  const course = setup.courseTitle.trim();
  const lectureFocus = lecture?.title.trim() || setup.lectureTitle.trim();
  if (!lectureFocus) return [];
  return uniqueQueries([
    [course, lectureFocus, "lecture"].filter(Boolean).join(" "),
    [lectureFocus, course, "explained"].filter(Boolean).join(" "),
    [lectureFocus, "university lecture"].filter(Boolean).join(" "),
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
