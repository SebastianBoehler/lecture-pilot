const CURLY_BRACE_LANGUAGES = new Set(["c", "c++", "cc", "cpp", "cxx", "h", "hpp", "java"]);

export function formatLegacyFencedCode(language: string, value: string) {
  const code = value.trim();
  if (
    code.includes("\n") ||
    !CURLY_BRACE_LANGUAGES.has(language.toLowerCase()) ||
    !/[{};]/.test(code)
  ) {
    return code;
  }
  return formatCurlyBraceCode(code);
}

function formatCurlyBraceCode(code: string) {
  const lines: string[] = [];
  let line = "";
  let indent = 0;
  let parentheses = 0;
  let quote = "";
  let escaped = false;
  let blockComment = false;

  function flush() {
    const content = line.trim();
    if (content) lines.push(`${"  ".repeat(indent)}${content}`);
    line = "";
  }

  for (let index = 0; index < code.length; index += 1) {
    const character = code[index];
    const next = code[index + 1];

    if (quote) {
      line += character;
      if (escaped) {
        escaped = false;
      } else if (character === "\\") {
        escaped = true;
      } else if (character === quote) {
        quote = "";
      }
      continue;
    }

    if (blockComment) {
      line += character;
      if (character === "*" && next === "/") {
        line += next;
        index += 1;
        blockComment = false;
      }
      continue;
    }

    if (character === "/" && next === "*") {
      line += "/*";
      index += 1;
      blockComment = true;
      continue;
    }

    if (character === "/" && next === "/") {
      line += code.slice(index);
      break;
    }

    if (character === '"' || character === "'") {
      quote = character;
      line += character;
      continue;
    }

    if (/\s/.test(character)) {
      if (line && !line.endsWith(" ")) line += " ";
      continue;
    }

    if (character === "(") {
      parentheses += 1;
      line += character;
      continue;
    }

    if (character === ")") {
      parentheses = Math.max(0, parentheses - 1);
      line += character;
      continue;
    }

    if (character === "{") {
      line = `${line.trimEnd()} {`;
      flush();
      indent += 1;
      continue;
    }

    if (character === "}") {
      flush();
      indent = Math.max(0, indent - 1);
      line = "}";
      const nextIndex = nextNonWhitespace(code, index + 1);
      const remaining = code.slice(nextIndex);
      if (/^(?:else|catch|finally|while)\b/.test(remaining)) {
        line += " ";
        index = nextIndex - 1;
      } else if (code[nextIndex] === ";") {
        index = nextIndex - 1;
      } else {
        flush();
      }
      continue;
    }

    line += character;
    if (character === ";" && parentheses === 0) flush();
  }

  flush();
  return lines.join("\n") || code;
}

function nextNonWhitespace(value: string, start: number) {
  let index = start;
  while (index < value.length && /\s/.test(value[index])) index += 1;
  return index;
}
