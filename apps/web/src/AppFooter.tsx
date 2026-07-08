export function AppFooter({
  onOpenHowItWorks,
  onOpenPrivacy,
}: {
  onOpenHowItWorks: () => void;
  onOpenPrivacy: () => void;
}) {
  return (
    <footer className="app-footer">
      <span>LecturePilot pilot</span>
      <nav aria-label="Project information">
        <button type="button" onClick={onOpenHowItWorks}>How it works</button>
        <button type="button" onClick={onOpenPrivacy}>Datenschutz</button>
      </nav>
    </footer>
  );
}
