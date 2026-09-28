import type { GateReviewQueueItem } from "./reviewQueueTypes";

function utcStamp(value: string) {
  return new Date(value)
    .toISOString()
    .replace(/[-:]/g, "")
    .replace(/\.\d{3}/, "");
}

async function eventId(item: GateReviewQueueItem) {
  const identity = `${item.course_id}:${item.lecture_id}:${item.gate_id}:${item.gate_revision}`;
  const hash = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(identity));
  return [...new Uint8Array(hash)].map((byte) => byte.toString(16).padStart(2, "0")).join("");
}

export async function reviewCalendar(items: GateReviewQueueItem[], now = new Date()) {
  const events = items.filter((item) => item.kind === "gate_review");
  const lines = [
    "BEGIN:VCALENDAR",
    "VERSION:2.0",
    "PRODID:-//LecturePilot//Review plan//EN",
    "CALSCALE:GREGORIAN",
    "METHOD:PUBLISH",
  ];
  for (const item of events) {
    const start = new Date(Math.max(new Date(item.due_at).getTime(), now.getTime()));
    const end = new Date(start.getTime() + 15 * 60_000);
    lines.push(
      "BEGIN:VEVENT",
      `UID:${await eventId(item)}@lecturepilot`,
      `DTSTAMP:${utcStamp(now.toISOString())}`,
      `DTSTART:${utcStamp(start.toISOString())}`,
      `DTEND:${utcStamp(end.toISOString())}`,
      "SUMMARY:LecturePilot review",
      "END:VEVENT",
    );
  }
  lines.push("END:VCALENDAR");
  return `${lines.map((line) => line.match(/.{1,75}/g)?.join("\r\n ") ?? "").join("\r\n")}\r\n`;
}

export async function downloadReviewCalendar(items: GateReviewQueueItem[]) {
  const url = URL.createObjectURL(
    new Blob([await reviewCalendar(items)], { type: "text/calendar" }),
  );
  const link = document.createElement("a");
  link.href = url;
  link.download = "lecturepilot-reviews.ics";
  link.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}
