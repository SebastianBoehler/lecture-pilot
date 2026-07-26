import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { MathText } from "./MathText";

describe("MathText fenced code", () => {
  it("promotes an embedded Java fence to a highlighted block", () => {
    const { container } = render(
      <MathText
        highlightedText={null}
        mode="block"
        text={
          "Inspect the boundary. ```java public static int lastZero(int[] x) { return -1; } ``` Then test it."
        }
      />,
    );

    expect(screen.getByText("Inspect the boundary.")).toBeInTheDocument();
    expect(screen.getByText("Then test it.")).toBeInTheDocument();
    const code = container.querySelector("pre code.language-java");
    expect(code).toHaveTextContent("public static int lastZero");
    expect(code?.querySelector(".hljs-keyword")).toHaveTextContent("public");
  });

  it("formats a legacy single-line Java control-flow example without splitting for-loop headers", () => {
    const { container } = render(
      <MathText
        highlightedText={null}
        mode="block"
        text={
          "```java int c1( int a, int b, int c ) { if ( a > b ) { for ( int i=0; i<b ; i++ ) { a += 1; } } } ```"
        }
      />,
    );

    expect(container.querySelector("pre code.language-java")?.textContent).toBe(
      [
        "int c1( int a, int b, int c ) {",
        "  if ( a > b ) {",
        "    for ( int i=0; i<b ; i++ ) {",
        "      a += 1;",
        "    }",
        "  }",
        "}",
        "",
      ].join("\n"),
    );
  });

  it("does not guess line breaks for non-curly-brace languages", () => {
    const { container } = render(
      <MathText
        highlightedText={null}
        mode="block"
        text={"```python if ready: print('go'); print('done') ```"}
      />,
    );

    expect(container.querySelector("pre code.language-python")).toHaveTextContent(
      "if ready: print('go'); print('done')",
    );
    expect(
      container.querySelector("pre code.language-python")?.textContent?.trimEnd(),
    ).not.toContain("\n");
  });
});
