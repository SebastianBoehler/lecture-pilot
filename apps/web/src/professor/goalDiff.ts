export type DiffGoal = Readonly<{ id: string; title: string; outcome: string }>;

export type GoalDiffEntry = Readonly<{
  kind: "kept" | "changed" | "added" | "removed";
  before?: DiffGoal;
  after?: DiffGoal;
}>;

/**
 * Compares previously approved goals with a regenerated proposal. Regenerated goals may carry
 * new ids, so goals also match by normalized title or outcome; each previous goal matches once.
 */
export function diffGoals(
  previous: readonly DiffGoal[],
  current: readonly DiffGoal[],
): GoalDiffEntry[] {
  const unmatched = [...previous];
  const take = (predicate: (goal: DiffGoal) => boolean) => {
    const index = unmatched.findIndex(predicate);
    return index < 0 ? undefined : unmatched.splice(index, 1)[0];
  };
  const entries: GoalDiffEntry[] = current.map((after) => {
    const before =
      take((goal) => goal.id === after.id) ??
      take((goal) => normalize(goal.title) === normalize(after.title)) ??
      take((goal) => normalize(goal.outcome) === normalize(after.outcome));
    if (!before) return { kind: "added", after };
    const same =
      normalize(before.title) === normalize(after.title) &&
      normalize(before.outcome) === normalize(after.outcome);
    return { kind: same ? "kept" : "changed", before, after };
  });
  return [...entries, ...unmatched.map((before) => ({ kind: "removed" as const, before }))];
}

function normalize(value: string) {
  return value.trim().replace(/\s+/g, " ").toLocaleLowerCase();
}
