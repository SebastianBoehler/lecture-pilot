import type { SectionSourceReference } from "./sourceReferences";
import type { WorkspaceResource } from "./types";

export function SourceMarker({
  reference,
  label,
  onOpenResource,
}: {
  reference: SectionSourceReference;
  label: string;
  onOpenResource: (resource: WorkspaceResource) => void;
}) {
  return (
    <button
      aria-label={`Open source ${reference.number} for ${label}`}
      className="inline-source-marker"
      type="button"
      onClick={() => onOpenResource(reference.resource)}
    >
      [{reference.number}]
    </button>
  );
}
