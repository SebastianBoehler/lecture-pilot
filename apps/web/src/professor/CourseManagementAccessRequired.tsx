export function CourseManagementAccessRequired({
  label,
  onBack,
}: {
  label: string;
  onBack: () => void;
}) {
  return (
    <main className="dashboard">
      <section aria-label={label} className="dashboard-header">
        <button className="ghost-button" type="button" onClick={onBack}>
          Back
        </button>
        <h1>Professor account required</h1>
        <p>Only professor and tenant admin accounts can access this workspace.</p>
      </section>
    </main>
  );
}
