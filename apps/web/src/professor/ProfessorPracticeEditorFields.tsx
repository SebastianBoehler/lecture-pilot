import { useId } from "react";

export function TextField({
  disabled,
  help,
  label,
  value,
  onChange,
}: {
  disabled: boolean;
  help?: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  const inputId = useId();
  const helpId = useId();
  return (
    <label htmlFor={inputId}>
      {label}
      {help ? <span id={helpId}>{help}</span> : null}
      <textarea
        aria-describedby={help ? helpId : undefined}
        disabled={disabled}
        id={inputId}
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  );
}

export function NumberField({
  disabled,
  help,
  label,
  value,
  onChange,
}: {
  disabled: boolean;
  help: string;
  label: string;
  value: number;
  onChange: (value: number) => void;
}) {
  const inputId = useId();
  const helpId = useId();
  return (
    <label htmlFor={inputId}>
      {label}
      <span id={helpId}>{help}</span>
      <input
        aria-describedby={helpId}
        disabled={disabled}
        id={inputId}
        max="365"
        min="1"
        type="number"
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
      />
    </label>
  );
}
