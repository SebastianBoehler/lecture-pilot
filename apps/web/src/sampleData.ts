import type { Lecture } from "./types";

export const lectures: Lecture[] = [
  {
    id: "lecture-01",
    number: "01",
    title: "Introduction and Learning Setup",
    date: "May 6",
    attendance: "present",
    materialPath: "courses/martius-ml/lectures/01/source.tex",
  },
  {
    id: "lecture-02",
    number: "02",
    title: "Linear Models and Generalization",
    date: "May 13",
    attendance: "unknown",
    materialPath: "courses/martius-ml/lectures/02/source.tex",
  },
  {
    id: "lecture-03",
    number: "03",
    title: "Kernels and Feature Maps",
    date: "Jun 4",
    attendance: "absent",
    materialPath: "courses/martius-ml/lectures/03/source.tex",
  },
];
