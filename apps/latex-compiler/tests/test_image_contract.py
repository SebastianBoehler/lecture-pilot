from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_image_pins_tectonic_and_proves_seeded_bundle_is_offline() -> None:
    dockerfile = (REPO_ROOT / "apps/latex-compiler/Dockerfile").read_text()
    seed = (REPO_ROOT / "apps/latex-compiler/bundle-seed.tex").read_text()
    format_seeds = {
        path.name: path.read_text()
        for path in (REPO_ROOT / "apps/latex-compiler/bundle-seeds").glob("*.tex")
    }

    assert "TECTONIC_VERSION=0.16.9" in dockerfile
    assert (
        "60b13a0826ae7ad9ce34b4a2df06bff2cfcfa6dda8a915477c0cbb84e1a4a902" in dockerfile
    )
    assert (
        "f9aa39017dbd51f111fdb93dda222178cbe51c8193508fc567b523cc74fff9c1" in dockerfile
    )
    assert "--only-cached" in dockerfile
    assert "bundle-seed.tex" in dockerfile
    assert "bundle-seeds" in dockerfile
    assert "chmod -R a=rX /var/cache/tectonic" in dockerfile
    assert "texlive-" not in dockerfile
    assert "pdflatex" not in dockerfile
    assert (
        "\\documentclass[notes=hide,10pt,mathserif,compress,aspectratio=169]{beamer}"
        in seed
    )
    assert {
        "article.tex",
        "report.tex",
        "book.tex",
        "bibliography.tex",
    } <= format_seeds.keys()
    assert "\\bibliography{references}" in format_seeds["bibliography.tex"]
