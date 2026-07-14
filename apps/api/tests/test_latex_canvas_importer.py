from pathlib import Path

from lecturepilot.latex_canvas_importer import import_latex_canvas
from lecturepilot.latex_canvas_text import clean_inline, read_math_blocks


def test_latex_import_keeps_long_lists_formulas_and_pdf_assets(tmp_path: Path) -> None:
    material_root = tmp_path / "course"
    image_dir = material_root / "images" / "Ch3"
    image_dir.mkdir(parents=True)
    _write_pdf(image_dir / "diagram.pdf")
    (image_dir / "figure.jpg").write_bytes(b"jpg")
    items = "\n".join(
        rf"\item Coverage item {index:02d} with enough learning words." for index in range(1, 26)
    )
    formulas = "\n".join(rf"\[ P(C_{index}\mid X) = {index} \]" for index in range(1, 7))
    source_path = material_root / "Lecture03-eng.tex"
    source_path.write_text(
        rf"""
\mytitle[29 April, 2025]{{3}}{{Bayesian Decision Theory}}
\begin{{frame}}{{Naive Bayes Classifiers}}
\ig{{Ch3/diagram.pdf}}
\ig{{Ch3/figure}}
\begin{{itemize}}
{items}
\end{{itemize}}
{formulas}
This paragraph carries additional conceptual content for the generated canvas.
\end{{frame}}
""",
        encoding="utf-8",
    )

    document = import_latex_canvas(
        source_path=source_path,
        material_root=material_root,
        course_id="martius-ml",
        lecture_id="lecture-03",
        workspace_path="canvas/index.md",
    )
    section = next(item for item in document.sections if item.id == "naive-bayes-classifiers")
    imported_items = [
        item for block in section.blocks if block.type == "list" for item in block.items
    ]
    list_blocks = [block for block in section.blocks if block.type == "list"]
    imported_assets = [block.asset_path for block in section.blocks if block.type == "asset"]
    imported_formulas = [block.text for block in section.blocks if block.type == "math"]

    assert len(imported_items) == 25
    assert len(list_blocks) == 1
    assert imported_assets == ["Ch3/diagram.pdf", "Ch3/figure.jpg"]
    assert len(imported_formulas) == 6


def test_overlay_assets_are_collapsed_and_not_front_loaded(tmp_path: Path) -> None:
    material_root = tmp_path / "course"
    image_dir = material_root / "images" / "Ch3"
    image_dir.mkdir(parents=True)
    for index in range(1, 4):
        _write_pdf(image_dir / f"Venn_C-X_{index}.pdf")
    source_path = material_root / "Lecture03-eng.tex"
    source_path.write_text(
        r"""
\mytitle[29 April, 2025]{3}{Bayesian Decision Theory}
\begin{frame}{Refresher: Conditional Probability}
This frame introduces conditional probability with a Venn diagram.
\ig{Ch3/Venn_C-X_1}
\ig{Ch3/Venn_C-X_2}
\ig{Ch3/Venn_C-X_3}
\end{frame}
""",
        encoding="utf-8",
    )

    document = import_latex_canvas(
        source_path=source_path,
        material_root=material_root,
        course_id="martius-ml",
        lecture_id="lecture-03",
        workspace_path="canvas/index.md",
    )
    section = next(item for item in document.sections if item.id == "bayes-formula")
    asset_index = next(index for index, block in enumerate(section.blocks) if block.type == "asset")
    paragraph_index = next(
        index for index, block in enumerate(section.blocks) if block.type == "paragraph"
    )

    assert [block.asset_path for block in section.blocks if block.type == "asset"] == [
        "Ch3/Venn_C-X_3.pdf"
    ]
    assert paragraph_index < asset_index


def test_latex_import_adds_original_slides_from_matching_pdf(tmp_path: Path) -> None:
    material_root = tmp_path / "course"
    source_path = material_root / "Lecture01-eng.tex"
    source_path.parent.mkdir(parents=True)
    source_path.write_text(
        r"""
\title{Lecture 1}
\begin{frame}{Learning topic}
Machine learning systems improve from data and evidence.
\end{frame}
""",
        encoding="utf-8",
    )
    _write_pdf(material_root / "Lecture01-eng.pdf")

    document = import_latex_canvas(
        source_path=source_path,
        material_root=material_root,
        course_id="martius-ml",
        lecture_id="lecture-01",
        workspace_path="canvas/index.md",
    )

    slide_section = next(
        section for section in document.sections if section.id == "original-slide-assets"
    )
    slide = slide_section.blocks[0]
    assert slide.asset_path.startswith("generated-slides/lecture-01/Lecture01-eng-")
    assert slide.asset_path.endswith("/slide-001.png")
    assert slide.caption == "Original slide 1 from Lecture01-eng.pdf"
    assert (material_root / slide.asset_path).read_bytes().startswith(b"\x89PNG")


def test_lecture_three_naive_bayes_frames_become_separate_canvas_sections(tmp_path: Path) -> None:
    material_root = tmp_path / "course"
    image_dir = material_root / "images" / "Ch3"
    image_dir.mkdir(parents=True)
    (image_dir / "spam-DALL-E.jpg").write_bytes(b"jpg")
    source_path = material_root / "Lecture03-eng.tex"
    source_path.write_text(
        r"""
\mytitle[29 April, 2025]{3}{Bayesian Decision Theory}
\begin{frame}{Naive Bayes Classifiers}
\begin{itemize}
\item The naive independence assumption replaces a hard joint likelihood with per-feature factors.
\item It assumes feature presence is independent once the class label is known.
\end{itemize}
\end{frame}
\begin{frame}{Advantages, Disadvantages and Application of Naive Bayes}
\begin{itemize}
\item It is simple and easy to implement for high-dimensional text inputs.
\item It naturally deals with imbalanced training data in many practical tasks.
\item It performs poorly when the independence assumptions are badly violated.
\end{itemize}
\end{frame}
\begin{frame}{Naive Bayes in Action: SPAM Filter}
\ig{Ch3/spam-DALL-E}
\begin{itemize}
\item Use wanted emails as HAM examples and unwanted emails as SPAM examples.
\item Store word probabilities from the labeled training emails.
\end{itemize}
\end{frame}
\begin{frame}{From text to tokens}
\begin{itemize}
\item Tokenization breaks the email text into words or tokens.
\item Lowercasing treats Email and email as the same token.
\item Stop words remove common function words before classification.
\end{itemize}
\end{frame}
\begin{frame}{Computing Probabilities}
\begin{itemize}
\item Count how often each token appears in examples from a class.
\item Divide by the total number of tokens from that class.
\end{itemize}
\end{frame}
\begin{frame}{Laplace Smoothing}
\begin{itemize}
\item Add a small pseudo count so unseen tokens do not force zero probability.
\end{itemize}
\end{frame}
\begin{frame}{Classifying a new Email}
\begin{itemize}
\item Multiply the learned token probabilities to score each possible class.
\end{itemize}
\end{frame}
\begin{frame}{Using log probabilities}
\begin{itemize}
\item Summing log probabilities avoids numerical underflow for long messages.
\end{itemize}
\end{frame}
\begin{frame}{Adjusting the decision boundary}
\begin{itemize}
\item Move the classification threshold when false positives are more costly.
\end{itemize}
\end{frame}
\begin{frame}{Receiver Operating Characteristics (ROC)}
ROC curves compare true-positive and false-positive rates across thresholds.
\end{frame}
""",
        encoding="utf-8",
    )

    document = import_latex_canvas(
        source_path=source_path,
        material_root=material_root,
        course_id="martius-ml",
        lecture_id="lecture-03",
        workspace_path="canvas/index.md",
    )
    sections = {section.id: section for section in document.sections}

    assert [section.id for section in document.sections] == [
        "naive-bayes-classifiers",
        "naive-bayes-tradeoffs",
        "spam-filter-example",
        "text-preprocessing-pipeline",
        "word-probability-estimates",
        "laplace-smoothing",
        "classifying-new-email",
        "log-probability-scores",
        "decision-boundary-and-roc",
    ]
    assert sections["naive-bayes-classifiers"].title == "Naive Bayes assumption"
    assert _list_size(sections["naive-bayes-classifiers"]) == 2
    assert _list_size(sections["spam-filter-example"]) == 2
    assert _list_size(sections["text-preprocessing-pipeline"]) == 3
    assert _list_size(sections["word-probability-estimates"]) == 2
    assert _list_size(sections["decision-boundary-and-roc"]) == 1


def test_align_math_is_wrapped_for_katex_display_rendering() -> None:
    formulas = read_math_blocks(
        r"""
\begin{align*}
  & \text{choose } C_i \text{ if } R(\alpha_i|x) < R(\alpha_k|x) \\
  & \text{choose reject otherwise}
\end{align*}
"""
    )

    assert formulas == [
        r"\begin{aligned}& \text{choose } C_i \text{ if } R(\alpha_i|x) < R(\alpha_k|x) \\ & \text{choose reject otherwise}\end{aligned}"
    ]


def test_linebreak_spacing_is_not_imported_as_display_math() -> None:
    formulas = read_math_blocks(
        r"""
First line\\[.5em]
\hfill Log identity: $\log(a\cdot b) = \log(a) + \log(b)$
\[
  \log(P(C|x)) \propto \log(P(C)) + \sum_i \log(P(x_i|C))
\]
"""
    )

    assert formulas == [r"\log(P(C|x)) \propto \log(P(C)) + \sum_i \log(P(x_i|C))"]


def test_inline_math_keeps_required_braces() -> None:
    text = clean_inline(
        r"$\rightarrow\ \hat{p}_0 = \frac{\sum\limits_{t=1}^N x^t}{N} = \frac{6}{9}$"
        r" and $=p(\x\mid C=1)P(C=1) \text{ }\text{ }\text{ } + $"
    )

    assert r"\frac{\sum\limits_{t=1}^N x^t}{N}" in text
    assert r"\text{ }\text{ }\text{ }" in text


def _list_size(section) -> int:
    return sum(len(block.items) for block in section.blocks if block.type == "list")


def _write_pdf(path: Path) -> None:
    import fitz

    document = fitz.open()
    page = document.new_page(width=120, height=80)
    page.insert_text((20, 40), "diagram")
    document.save(path)
    document.close()
