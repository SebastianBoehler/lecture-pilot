export function validateWebMcpInput(
  raw: unknown,
  properties: Record<string, unknown>,
  required: string[],
) {
  if (!raw || typeof raw !== "object" || Array.isArray(raw))
    throw new Error("Expected an input object.");
  const input = raw as Record<string, unknown>;
  for (const key of Object.keys(input)) {
    if (!Object.hasOwn(properties, key)) throw new Error(`Unexpected input: ${key}.`);
    const schema = properties[key] as { enum?: string[] };
    const value = input[key];
    if (
      typeof value !== "string" ||
      !value.length ||
      value.length > 200 ||
      (schema.enum && !schema.enum.includes(value))
    ) {
      throw new Error(`Invalid ${key}.`);
    }
  }
  for (const key of required) if (!(key in input)) throw new Error(`Missing ${key}.`);
  return input;
}
