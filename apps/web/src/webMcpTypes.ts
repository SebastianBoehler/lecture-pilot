// Producer subset of the WebMCP draft, 4 September 2026.
export type WebMcpTool = {
  name: string;
  description: string;
  inputSchema: Record<string, unknown>;
  annotations: { readOnlyHint: boolean; untrustedContentHint: boolean };
  execute: (input: unknown) => Promise<unknown>;
};

export type WebMcpContext = {
  registerTool: (tool: WebMcpTool, options: { signal: AbortSignal }) => Promise<void>;
};
