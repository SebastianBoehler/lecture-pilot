from __future__ import annotations

from pathlib import Path

from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.latex_canvas_importer import CANVAS_IMPORT_VERSION


def write_course_source(tmp_path: Path) -> Path:
    material_root = tmp_path / "course"
    image_dir = material_root / "images" / "Ch3"
    image_dir.mkdir(parents=True)
    (image_dir / "spam-DALL-E.jpg").write_bytes(b"not-a-real-jpeg")
    (material_root / "Lecture01-eng.tex").write_text(_LECTURE_01, encoding="utf-8")
    (material_root / "Lecture02-eng.tex").write_text(_LECTURE_02, encoding="utf-8")
    (material_root / "Lecture03-eng.tex").write_text(_LECTURE_03, encoding="utf-8")
    return material_root


def course_canvas(section_id: str, title: str) -> CanvasDocument:
    return CanvasDocument(
        id="martius-ml-lecture-03",
        import_version=CANVAS_IMPORT_VERSION,
        course_id="martius-ml",
        lecture_id="lecture-03",
        title="Generated base",
        source_kind="generated",
        source_ref="course planner from Lecture03-eng.tex",
        workspace_path="course/index.md",
        sections=[
            CanvasSection(
                id=section_id,
                title=title,
                source_ref="Lecture03-eng.tex frame 1",
                blocks=[CanvasBlock(id=f"{section_id}-p-1", type="paragraph", text=f"{title} content.")],
            )
        ],
    )


def published_course_canvas(course_id: str, lecture_id: str) -> CanvasDocument:
    return CanvasDocument(
        id=f"{course_id}-{lecture_id}",
        course_id=course_id,
        lecture_id=lecture_id,
        title="Published lecture",
        source_kind="generated",
        source_ref="test fixture",
        workspace_path="course/index.md",
        sections=[
            CanvasSection(
                id="intro",
                title="Intro",
                source_ref="test fixture",
                blocks=[CanvasBlock(id="intro-p", type="paragraph", text="Published.")],
            )
        ],
    )


_LECTURE_01 = r"""
\mytitle[6 May, 2026]{1}{Introduction}
\begin{frame}{Course setup}
This lecture explains course logistics and the machine learning overview.
\end{frame}
"""

_LECTURE_02 = r"""
\mytitle[13 May, 2026]{2}{Linear Models and Generalization}
\begin{frame}{Linear model recap}
Linear models combine features and weights before studying generalization.
\end{frame}
"""

_LECTURE_03 = r"""
\mytitle[29 April, 2025]{3}{Bayesian Decision Theory}
\begin{frame}{Rückmeldung aus Vorlesung 2}
\item Administrative feedback only.
\end{frame}
\begin{frame}{Bayesian Decision Theory: The Aim}
\ig{Ch3/spam-DALL-E}
\begin{itemize}
\item Use probabilities to make decisions.
\end{itemize}
Bayesian decision theory connects evidence, posterior probabilities, and decisions.
\end{frame}
\begin{frame}{Bayes Formula}
\begin{itemize}
\item Prior belief
\item Likelihood
\item Evidence
\end{itemize}
Bayes formula turns evidence into a posterior for a classification problem.
\[
P(C\mid X) = \frac{P(X\mid C)P(C)}{P(X)}
\]
\end{frame}
\begin{frame}{Classification}
We classify an email as SPAM if the predicted probability is larger than $\rho$.
\end{frame}
\begin{frame}{Bayes Rule: To Sum Up}
Prior, likelihood, evidence, and posterior determine the classifier score.
\end{frame}
\begin{frame}{Naive Bayes Classifiers}
The independence assumption reduces joint probabilities to per-feature probabilities.
\begin{itemize}
\item This assumption simplifies the computation of likelihood term:
\[
P(x_1, ..., x_n | C) = P(x_1 | C) \cdot \ldots \cdot P(x_n | C)
\]
\item we reduce the complexity: \\ instead of computing joint probabilities of all features
\end{itemize}
\end{frame}
\begin{frame}{Losses and Risks}
Expected risk compares actions when mistakes have different costs.
\[
R(\alpha_i|x) = \sum\limits_{k=1}^K \lambda_{ik}P(C_k|x)
\]
\end{frame}
"""
