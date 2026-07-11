export function installVitePreloadRecovery(
  target: Window,
  reload: () => void = () => target.location.reload(),
) {
  const recover = (event: Event) => {
    event.preventDefault();
    reload();
  };
  target.addEventListener("vite:preloadError", recover);
  return () => target.removeEventListener("vite:preloadError", recover);
}
