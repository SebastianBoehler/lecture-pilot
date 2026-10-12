import type { ProfessorUsageSummary } from "./usageTypes";

export function usageHistory(
  usage: Pick<ProfessorUsageSummary, "period_start" | "period_end" | "daily">,
) {
  const byDate = new Map(usage.daily.map((day) => [day.date, day]));
  const days: ProfessorUsageSummary["daily"] = [];
  const end = Date.parse(`${usage.period_end}T00:00:00Z`);
  for (let date = Date.parse(`${usage.period_start}T00:00:00Z`); date <= end; date += 86400000) {
    const key = new Date(date).toISOString().slice(0, 10);
    days.push(
      byDate.get(key) ?? {
        date: key,
        model_requests: 0,
        tutor_turns: 0,
        total_tokens: 0,
        images: 0,
      },
    );
  }
  return days;
}
