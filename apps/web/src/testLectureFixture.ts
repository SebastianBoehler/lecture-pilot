import type { Lecture } from "./types";

export const lectures: Lecture[] = [
  {
    id: "lecture-01",
    number: "01",
    title: "Introduction and Learning Setup",
    date: "May 6",
    attendance: "present",
    materialPath: "Lecture01-eng.tex",
  },
  {
    id: "lecture-02",
    number: "02",
    title: "Linear Models and Generalization",
    date: "May 13",
    attendance: "unknown",
    materialPath: "Lecture02-eng.tex",
  },
  {
    id: "lecture-03",
    number: "03",
    title: "Bayesian Decision Theory",
    date: "Jun 4",
    attendance: "absent",
    materialPath: "Lecture03-eng.tex",
  },
];
