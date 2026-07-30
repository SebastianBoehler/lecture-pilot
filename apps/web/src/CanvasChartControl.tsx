import type { CanvasComponentData } from "./types";

type CanvasChartControlProps = {
  activeIndex: number;
  controlLabel: string;
  data: CanvasComponentData;
  onChange: (index: number) => void;
};

export function CanvasChartControl({
  activeIndex,
  controlLabel,
  data,
  onChange,
}: CanvasChartControlProps) {
  if (data.control_type === "buttons") {
    return (
      <div aria-label={controlLabel} className="canvas-chart-control" role="group">
        <span>{controlLabel}</span>
        <div className="canvas-chart-buttons">
          {data.frames.map((frame, index) => (
            <button
              aria-pressed={index === activeIndex}
              key={`${index}-${frame.label}`}
              onClick={() => onChange(index)}
              type="button"
            >
              {frame.label}
            </button>
          ))}
        </div>
      </div>
    );
  }

  const frame = data.frames[activeIndex];
  return (
    <label className="canvas-chart-control">
      <span>
        {controlLabel}: <strong>{frame.label}</strong>
      </span>
      <input
        aria-label={controlLabel}
        max={data.frames.length - 1}
        min="0"
        onChange={(event) => onChange(Number(event.currentTarget.value))}
        step="1"
        type="range"
        value={activeIndex}
      />
    </label>
  );
}
