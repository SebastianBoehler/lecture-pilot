from __future__ import annotations

import argparse
import base64
from dataclasses import dataclass
from io import BytesIO
import http.client
import json
from urllib.parse import quote, urlsplit
from zipfile import ZIP_DEFLATED, ZipFile


@dataclass(frozen=True)
class Case:
    name: str
    main_path: str
    files: dict[str, bytes | str]
    should_compile: bool = True


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Exercise the offline Tectonic service against synthetic course formats."
    )
    parser.add_argument("--compiler-url", required=True)
    args = parser.parse_args()
    results = [_run_case(args.compiler_url, case) for case in _cases()]
    print(json.dumps({"compiler_url": args.compiler_url, "results": results}, indent=2))
    if any(result["status"] != "pass" for result in results):
        raise SystemExit(1)


def _run_case(compiler_url: str, case: Case) -> dict[str, object]:
    archive = BytesIO()
    with ZipFile(archive, "w", ZIP_DEFLATED) as bundle:
        for path, content in case.files.items():
            bundle.writestr(
                path, content.encode() if isinstance(content, str) else content
            )
    payload = archive.getvalue()
    parsed = urlsplit(compiler_url)
    connection_type = (
        http.client.HTTPSConnection
        if parsed.scheme == "https"
        else http.client.HTTPConnection
    )
    connection = connection_type(parsed.hostname, parsed.port, timeout=60)
    endpoint = (
        f"{parsed.path.rstrip('/')}/compile?main_path={quote(case.main_path, safe='')}"
    )
    try:
        connection.request(
            "POST",
            endpoint,
            body=payload,
            headers={"Content-Type": "application/zip"},
        )
        response = connection.getresponse()
        output = response.read()
    finally:
        connection.close()
    compiled = response.status == 200 and output.startswith(b"%PDF-")
    passed = compiled == case.should_compile
    return {
        "case": case.name,
        "expected": "compile" if case.should_compile else "reject",
        "http_status": response.status,
        "pdf_bytes": len(output) if compiled else None,
        "status": "pass" if passed else "unexpected",
    }


def _cases() -> list[Case]:
    return [
        _messy_beamer_case(),
        _article_case(),
        _nested_report_case(),
        _book_case(),
        _custom_class_case(),
        _bibtex_case(),
        _legacy_encoding_case(),
        _shell_escape_case(),
        _missing_package_case(),
        _svg_case(),
    ]


def _messy_beamer_case() -> Case:
    return Case(
        "nested-beamer-custom-macros-unicode-mixed-case-image",
        "Weeks/Week 01/Main.tex",
        {
            "Weeks/Week 01/Main.tex": r"""
\documentclass{beamer}
\graphicspath{{Images/}}
\input{Sections/Formulas}
\input{shared/macros}
\begin{document}
\begin{frame}{Grüße aus Tübingen}
  $\courseformula{A}{x}{b}\quad \indicator_A$
  \includegraphics[width=1cm]{plot}
\end{frame}
\end{document}
""",
            "Weeks/Week 01/Sections/Formulas.tex": (
                r"\usepackage{dsfont}\newcommand{\indicator}{\mathds{1}}"
            ),
            "shared/macros.tex": r"""
\usepackage{amsmath,bm}
\newcommand{\courseformula}[3]{\operatorname*{arg\,min}_{\bm{#2}}\lVert #1#2-#3\rVert_2}
""",
            "Images/Plot.PNG": _png(),
        },
    )


def _article_case() -> Case:
    return Case(
        "article-math-theorem-table-german",
        "notes.tex",
        {
            "notes.tex": r"""
\documentclass{article}
\usepackage[ngerman]{babel}
\usepackage{amsmath,amssymb,amsthm,booktabs,longtable}
\newtheorem{satz}{Satz}
\begin{document}
\begin{satz}Für $x\in\mathbb{R}$ gilt $x^2\geq0$.\end{satz}
\begin{longtable}{lr}\toprule Wert&Zahl\\\midrule Ä&1\\\bottomrule\end{longtable}
\end{document}
""",
        },
    )


def _nested_report_case() -> Case:
    return Case(
        "nested-report-local-and-root-inputs",
        "Course/Semester/Report.tex",
        {
            "Course/Semester/Report.tex": r"""
\documentclass{report}
\input{Chapters/One}
\input{shared}
\begin{document}\chapter{Overview}\localtext\ \roottext\end{document}
""",
            "Course/Semester/Chapters/One.tex": r"\newcommand{\localtext}{local}",
            "shared.tex": r"\newcommand{\roottext}{root}",
        },
    )


def _book_case() -> Case:
    return Case(
        "book-class-toc",
        "book.tex",
        {
            "book.tex": r"""
\documentclass{book}
\begin{document}\tableofcontents\chapter{A}\section{B}Text\end{document}
"""
        },
    )


def _custom_class_case() -> Case:
    return Case(
        "custom-document-class",
        "Lectures/main.tex",
        {
            "Lectures/main.tex": r"""
\documentclass{course-notes}
\begin{document}\courseheading\end{document}
""",
            "course-notes.cls": r"""
\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{course-notes}
\LoadClass{article}
\newcommand{\courseheading}{Custom course class}
""",
        },
    )


def _bibtex_case() -> Case:
    return Case(
        "bibtex-references",
        "Paper/main.tex",
        {
            "Paper/main.tex": r"""
\documentclass{article}
\begin{document}\cite{source}\bibliographystyle{plain}\bibliography{references}\end{document}
""",
            "references.bib": "@book{source,author={Ada Lovelace},title={Notes},year={1843}}",
        },
    )


def _legacy_encoding_case() -> Case:
    return Case(
        "latin1-source",
        "legacy.tex",
        {
            "legacy.tex": (
                b"\\documentclass{article}\n\\usepackage[latin1]{inputenc}\n"
                b"\\begin{document}Gr\xfc\xdfe\\end{document}\n"
            )
        },
    )


def _shell_escape_case() -> Case:
    return Case(
        "shell-escape-remains-disabled",
        "unsafe.tex",
        {
            "unsafe.tex": r"""
\documentclass{article}
\begin{document}
\immediate\write18{touch escaped}
\IfFileExists{escaped}{unsafe}{\GenericError{}{shell escape disabled}{}{} }
\end{document}
""",
        },
        should_compile=False,
    )


def _missing_package_case() -> Case:
    return Case(
        "unseeded-private-package",
        "missing.tex",
        {
            "missing.tex": r"""
\documentclass{article}
\usepackage{professor-private-package}
\begin{document}Missing\end{document}
"""
        },
        should_compile=False,
    )


def _svg_case() -> Case:
    return Case(
        "raw-svg-needs-preconversion",
        "svg.tex",
        {
            "svg.tex": r"""
\documentclass{article}
\usepackage{graphicx}
\begin{document}\includegraphics{diagram.svg}\end{document}
""",
            "diagram.svg": '<svg xmlns="http://www.w3.org/2000/svg"><rect width="1" height="1"/></svg>',
        },
        should_compile=False,
    )


def _png() -> bytes:
    return base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
    )


if __name__ == "__main__":
    main()
