import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { DisplayMath, MathText } from "./MathText";

describe("MathText", () => {
  it("renders light markdown emphasis around inline math", () => {
    render(<p><MathText highlightedText={null} text="Use **posterior** with `p(x | C)` and $P(C|x)$." /></p>);

    expect(screen.getByText("posterior").closest("strong")).not.toBeNull();
    expect(screen.getByText("p(x | C)").tagName).toBe("CODE");
    expect(document.querySelector(".katex")).not.toBeNull();
  });

  it("renders undelimited LaTeX commands inside prose and highlights", () => {
    render(
      <p>
        <MathText
          highlightedText="loss function \\lambda_{ik}"
          text="We define a loss function \\lambda_{ik} and threshold \\rho."
        />
      </p>,
    );

    expect(document.querySelectorAll(".katex")).toHaveLength(2);
    expect(document.querySelector(".phrase-highlight")?.textContent).toBe("loss function");
  });

  it("renders bracketed display math embedded in imported slide text", () => {
    render(
      <p>
        <MathText
          highlightedText={null}
          text="This assumption simplifies the likelihood: \\[ P(x_1, ..., x_n | C) = P(x_1 | C) P(x_n | C) \\]"
        />
      </p>,
    );

    expect(document.body.textContent).not.toContain("\\[");
    expect(document.querySelector(".katex-display")).not.toBeNull();
  });

  it("renders generated math blocks that contain inline formulas and prose", () => {
    render(
      <DisplayMath
        expression={[
          "The state update and output equations are:",
          "$z_h^t = f \\left( \\sum_{j=0}^d w_{hj}x_j^t + \\sum^H_{l=0} r_{hl}z_l^{t-1}\\right)$",
          "and $y^t = g \\left( \\sum^H_{h=0} v_h z_h^t \\right)$.",
        ].join(" ")}
      />,
    );

    expect(screen.getByText(/state update and output equations/i)).toBeInTheDocument();
    expect(document.querySelector(".katex-error")).toBeNull();
    expect(document.querySelectorAll(".katex")).toHaveLength(2);
  });

  it("renders course-defined LaTeX macros used in Martius lecture sources", () => {
    render(
      <p>
        <MathText
          highlightedText={null}
          text={String.raw`Use $\spr{a}{b}=\Red{\mathbf f^\T_a}\Blue{\mathbf f_b}$ and $\argmin_{x \in \R}\pDiff{\L}{w}$.`}
        />
      </p>,
    );

    expect(document.querySelector(".katex-error")).toBeNull();
    expect(document.querySelectorAll(".katex")).toHaveLength(2);
  });

  it("renders course emphasis macros inside display math", () => {
    render(<DisplayMath expression={String.raw`h(x)=y \quad \text{ for \imp{new} } x,y \text{ pairs.}`} />);

    expect(document.body.textContent).toContain("new");
    expect(document.querySelector(".katex-error")).toBeNull();
    expect(document.querySelector(".katex-display")).not.toBeNull();
  });

  it("renders full markdown blocks with lists, tables, links, and math", () => {
    render(
      <div>
        <MathText
          highlightedText={null}
          mode="block"
          text={[
            "### Prerequisites",
            "",
            "* **Probability** with $P(C|x)$",
            "* `Python` basics",
            "",
            "| Skill | Why |",
            "| --- | --- |",
            "| Linear algebra | vectors |",
            "",
            "[Course page](https://example.com)",
          ].join("\n")}
        />
      </div>,
    );

    expect(screen.getByRole("heading", { name: "Prerequisites" })).toBeInTheDocument();
    expect(screen.getByText("Probability").closest("strong")).not.toBeNull();
    expect(screen.getByText("Python").tagName).toBe("CODE");
    expect(screen.getByRole("table")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Course page" })).toHaveAttribute("href", "https://example.com");
    expect(document.querySelector(".katex")).not.toBeNull();
  });

  it("highlights a useful prefix when the model returns a truncated phrase", () => {
    render(
      <p>
        <MathText
          highlightedText="Bayesian decision theory provides a framework for making optimal decisions when outcomes are unce..."
          text="Bayesian decision theory provides a framework for making optimal decisions when outcomes are uncertain."
        />
      </p>,
    );

    expect(document.querySelector(".phrase-highlight")?.textContent).toContain(
      "Bayesian decision theory provides a framework",
    );
  });
});
