import type { MouseEvent } from "react";

export function dismissDialogFromBackdrop(
  event: MouseEvent<HTMLDialogElement>,
  onDismiss: () => void,
  disabled = false,
) {
  if (!disabled && event.target === event.currentTarget) onDismiss();
}
