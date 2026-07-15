export async function runBoundedTasks<T>(
  items: T[],
  concurrency: number,
  task: (item: T, index: number) => Promise<void>,
) {
  let nextIndex = 0;
  let failure: unknown;
  let stopped = false;
  const workerCount = Math.min(concurrency, items.length);
  await Promise.all(
    Array.from({ length: workerCount }, async () => {
      while (!stopped && nextIndex < items.length) {
        const index = nextIndex;
        nextIndex += 1;
        try {
          await task(items[index], index);
        } catch (error) {
          if (!stopped) failure = error;
          stopped = true;
        }
      }
    }),
  );
  if (stopped) throw failure;
}
