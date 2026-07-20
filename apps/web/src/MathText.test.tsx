import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { DisplayMath, MathText } from "./MathText";

describe("MathText", () => {
  it("renders light markdown emphasis around inline math", () => {
    render(
      <p>
        <MathText highlightedText={null} text="Use **posterior** with `p(x | C)` and $P(C|x)$." />
      </p>,
    );

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

  it("renders complete braced LaTeX commands inside generated prose", () => {
    render(
      <p>
        <MathText
          highlightedText={null}
          text={String.raw`The dataset notation \mathcal{D}, hypothesis h(\mathbf{x}), and loss \mathcal{L} clarify the objective.`}
        />
      </p>,
    );

    expect(document.querySelector(".katex-error")).toBeNull();
    expect(document.querySelectorAll(".katex")).toHaveLength(3);
    expect(document.querySelectorAll(".katex")[1]?.textContent).toContain("h(x)");
  });

  it("renders a complete undelimited equation inside generated prose", () => {
    render(
      <p>
        <MathText
          highlightedText={null}
          text={String.raw`Worked example: Hypothesis: h(\mathbf{x}) = \mathbf{w}^T \mathbf{x}. Steps: define the loss.`}
        />
      </p>,
    );

    expect(document.querySelector(".katex-error")).toBeNull();
    expect(document.querySelectorAll(".katex")).toHaveLength(1);
    expect(document.querySelector(".katex")?.textContent).toContain("h(x)=wTx");
  });

  it("does not treat equality inside a subscript group as an equation boundary", () => {
    render(
      <p>
        <MathText
          highlightedText={null}
          text={String.raw`Examples are written as ordered pairs {\mathbf{x}^t, y^t}_{t=1}^N where each index selects one sample.`}
        />
      </p>,
    );

    expect(document.querySelector(".katex-error")).toBeNull();
    expect(document.querySelectorAll(".katex")).toHaveLength(1);
    expect(document.body).toHaveTextContent("where each index selects one sample");
  });

  it("keeps sized LaTeX delimiter pairs in one renderable expression", () => {
    render(
      <p>
        <MathText
          highlightedText={null}
          text={String.raw`Choose \sum_{t=1}^N \sum_{i=1}^K 1\left(h_i(\mathbf{x}^t) \neq y_i^t\right).`}
        />
      </p>,
    );

    expect(document.querySelector(".katex-error")).toBeNull();
    expect(document.querySelectorAll(".katex")).toHaveLength(3);
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
    render(
      <DisplayMath
        expression={String.raw`h(x)=y \quad \text{ for \imp{new} } x,y \text{ pairs.}`}
      />,
    );

    expect(document.body.textContent).toContain("new");
    expect(document.querySelector(".katex-error")).toBeNull();
    expect(document.querySelector(".katex-display")).not.toBeNull();
  });

  it("keeps explanatory prose readable beside an undelimited display equation", () => {
    render(
      <DisplayMath
        expression={String.raw`The empirical risk is minimized by L(f) = \frac{1}{n}\sum_{i=1}^{n}\ell(f(x_i), y_i)`}
      />,
    );

    const prose = screen.getByText("The empirical risk is minimized by");
    expect(prose.closest(".katex")).toBeNull();
    expect(document.querySelector(".katex-display")).not.toBeNull();
    expect(document.querySelector(".math-render-fallback")).toBeNull();
  });

  it("separates multiple explanatory clauses from their equations", () => {
    render(
      <DisplayMath
        expression={String.raw`The regularized loss is: L' = L + \lambda\lVert w\rVert^2. During optimization, the update is: w_i = w_i - \eta\nabla_i L`}
      />,
    );

    expect(screen.getByText("The regularized loss is:").closest(".katex")).toBeNull();
    expect(screen.getByText("During optimization, the update is:").closest(".katex")).toBeNull();
    expect(document.querySelectorAll(".katex-display")).toHaveLength(2);
  });

  it("keeps trailing explanatory prose out of the equation renderer", () => {
    render(
      <DisplayMath
        expression={String.raw`The latent process is: z_t = \mu_t + \epsilon_t, where epsilon~N(0,1).`}
      />,
    );

    expect(screen.getByText("where epsilon~N(0,1).").closest(".katex")).toBeNull();
    expect(document.querySelectorAll(".katex-display")).toHaveLength(1);
  });

  it("separates an unpunctuated explanatory continuation from display math", () => {
    render(
      <DisplayMath expression={String.raw`The optimum is w = 0 where the gradient vanishes`} />,
    );

    expect(screen.getByText("where the gradient vanishes").closest(".katex")).toBeNull();
    expect(document.querySelectorAll(".katex-display")).toHaveLength(1);
  });

  it("keeps pure undelimited formulas on the KaTeX display path", () => {
    render(<DisplayMath expression={String.raw`R(f) = \mathbb{E}[\ell(f(X), Y)]`} />);

    expect(document.querySelector(".katex-display")).not.toBeNull();
    expect(document.querySelector(".math-render-fallback")).toBeNull();
  });

  it("keeps valid multiline LaTeX environments intact", () => {
    render(
      <DisplayMath
        expression={String.raw`\begin{aligned}
f(x) &= x^2 && \text{if } x \geq 0 \\
f(x) &= -x && \text{if } x < 0
\end{aligned}`}
      />,
    );

    expect(document.querySelectorAll(".katex-display")).toHaveLength(1);
    expect(document.body).toHaveTextContent("if");
    expect(document.querySelector(".math-render-fallback")).toBeNull();
  });

  it("shows unsupported display math as an explicit readable fallback", () => {
    const expression = String.raw`\courseSpecificRisk{f} = \frac{1}{`;
    render(<DisplayMath expression={expression} />);

    const fallback = screen.getByText("Formula could not be rendered").closest("[role='note']");
    expect(fallback).not.toBeNull();
    expect(fallback).toHaveClass("math-render-fallback");
    expect(fallback).toHaveTextContent("Formula could not be rendered");
    expect(fallback).toHaveTextContent(expression);
    expect(document.querySelector(".katex")).toBeNull();
  });

  it("shows unsupported delimited math as the same readable fallback", () => {
    const expression = String.raw`Objective: $\courseSpecificRisk{f}$`;
    render(<DisplayMath expression={expression} />);

    const fallback = screen.getByText("Formula could not be rendered").closest("[role='note']");
    expect(fallback).toHaveTextContent(expression);
    expect(document.querySelector(".katex-error")).toBeNull();
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
    expect(screen.getByRole("link", { name: "Course page" })).toHaveAttribute(
      "href",
      "https://example.com",
    );
    expect(document.querySelector(".katex")).not.toBeNull();
  });

  it("renders notebook code cells as inert fenced code", () => {
    const { container } = render(
      <MathText
        highlightedText={null}
        mode="block"
        text={"```python\ndef step(theta, gradient):\n    return theta - gradient\n```"}
      />,
    );

    const code = container.querySelector("pre code.language-python");
    expect(code).not.toBeNull();
    expect(code?.textContent).toContain("return theta - gradient");
    expect(container.querySelector("script")).toBeNull();
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
