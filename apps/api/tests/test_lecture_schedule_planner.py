from datetime import date

from lecturepilot.lecture_schedule import propose_lecture_schedule
from lecturepilot.source_bundle import SourceBundleFile


def test_schedule_infers_all_detected_lectures_before_requested_count(tmp_path) -> None:
    first = tmp_path / "Lecture01-eng.tex"
    second = tmp_path / "Lecture02-eng.tex"
    first.write_text(r"\section{Introduction}", encoding="utf-8")
    second.write_text(r"\section{Bayes}", encoding="utf-8")

    proposal = propose_lecture_schedule(
        course_id="martius-ml",
        files=[_source_file(first), _source_file(second)],
        roots=[tmp_path],
        first_lecture_date=date(2026, 5, 6),
        requested_count=1,
    )

    assert [lecture.number for lecture in proposal.lectures] == ["01", "02"]


def test_schedule_prefers_topic_section_over_housekeeping_frames(tmp_path) -> None:
    source = tmp_path / "Lecture03-eng.tex"
    source.write_text(
        r"""
        \begin{frame}{Note}Housekeeping\end{frame}
        \begin{frame}{Course Thread}Admin\end{frame}
        \section{Bayesian Decision Theory}
        \begin{frame}{Bayes Rule}
        Posterior probabilities combine prior, likelihood and evidence.
        \end{frame}
        """,
        encoding="utf-8",
    )

    proposal = propose_lecture_schedule(
        course_id="martius-ml",
        files=[_source_file(source)],
        roots=[tmp_path],
        first_lecture_date=date(2026, 5, 6),
    )

    assert proposal.lectures[0].title == "Bayesian Decision Theory"


def test_schedule_uses_explicit_slide_dates(tmp_path) -> None:
    first = tmp_path / "Lecture01-eng.tex"
    second = tmp_path / "Lecture02-eng.tex"
    first.write_text(r"\date{May 6, 2026}\section{Introduction}", encoding="utf-8")
    second.write_text(r"\date{13.05.2026}\section{Generalization}", encoding="utf-8")

    proposal = propose_lecture_schedule(
        course_id="martius-ml",
        files=[_source_file(first), _source_file(second)],
        roots=[tmp_path],
    )

    assert [lecture.date.isoformat() for lecture in proposal.lectures] == [
        "2026-05-06",
        "2026-05-13",
    ]


def test_schedule_anchors_missing_dates_from_detected_slide_date(tmp_path) -> None:
    first = tmp_path / "Lecture01-eng.tex"
    second = tmp_path / "Lecture02-eng.tex"
    first.write_text(r"\section{Introduction}", encoding="utf-8")
    second.write_text(r"\date{2026-05-13}\section{Generalization}", encoding="utf-8")

    proposal = propose_lecture_schedule(
        course_id="martius-ml",
        files=[_source_file(first), _source_file(second)],
        roots=[tmp_path],
    )

    assert [lecture.date.isoformat() for lecture in proposal.lectures] == [
        "2026-05-06",
        "2026-05-13",
    ]


def _source_file(path) -> SourceBundleFile:
    return SourceBundleFile(path=path.name, kind="latex", size_bytes=path.stat().st_size)
