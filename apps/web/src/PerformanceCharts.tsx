import type { CSSProperties } from "react";

import { percent } from "./performanceMetrics";
import type { LectureAnalyticsSummary } from "./types";

export function AnalyticsChart({ analytics }: { analytics: LectureAnalyticsSummary }) {
  const quiz = analytics.quizzes[0];
  const gate = analytics.gates[0];
  const quizRate = quiz?.correct_rate ?? 0;
  const passed = gate?.status_counts.passed ?? 0;
  const gateRate = gate?.total_events ? passed / gate.total_events : 0;
  return (
    <section className="performance-chart" aria-label="Lecture analytics chart">
      <div>
        <span>Quiz success</span>
        <strong>{percent(quizRate)}</strong>
        <MiniDonut value={quizRate} tone="success" />
      </div>
      <div>
        <span>Gate pass rate</span>
        <strong>{percent(gateRate)}</strong>
        <MiniDonut value={gateRate} tone="warning" />
      </div>
      <div className="attendance-chart">
        <span>Attendance mix</span>
        <StackedBar values={quiz?.attendance_split ?? gate?.attendance_split ?? {}} />
      </div>
    </section>
  );
}

function MiniDonut({ value, tone }: { value: number; tone: "success" | "warning" }) {
  const radius = 16;
  const circumference = 2 * Math.PI * radius;
  return (
    <svg className={`mini-donut is-${tone}`} viewBox="0 0 42 42" aria-hidden="true">
      <circle cx="21" cy="21" r={radius} />
      <circle
        cx="21"
        cy="21"
        r={radius}
        pathLength={circumference}
        strokeDasharray={`${Math.max(0, Math.min(1, value)) * circumference} ${circumference}`}
      />
    </svg>
  );
}

function StackedBar({ values }: { values: Record<string, number> }) {
  const total = Object.values(values).reduce((sum, value) => sum + value, 0);
  return (
    <div className="stacked-bar">
      {Object.entries(values).map(([label, value]) => (
        <span
          className={`is-${label}`}
          key={label}
          style={{ "--segment-width": `${total ? Math.round((value / total) * 100) : 0}%` } as CSSProperties}
        >
          {label} {value}
        </span>
      ))}
    </div>
  );
}
