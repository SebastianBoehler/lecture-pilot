export const PROFESSOR_WALKTHROUGH_EVENT = "lecturepilot:start-professor-walkthrough";
const PROFESSOR_WALKTHROUGH_VERSION = "v2";

export function requestProfessorWalkthrough() {
  window.dispatchEvent(new Event(PROFESSOR_WALKTHROUGH_EVENT));
}

export function hasSeenProfessorWalkthrough(username: string) {
  return window.localStorage.getItem(walkthroughStorageKey(username)) === "seen";
}

export function walkthroughStorageKey(username: string) {
  return `lecturepilot.professor-walkthrough.${PROFESSOR_WALKTHROUGH_VERSION}.${username}`;
}
