import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { createPublicWebMcpTools } from "./publicWebMcpTools";
import { hasStudentWebMcpCredentials } from "./webMcpSession";
import { createWebMcpTools, type WebMcpState } from "./webMcpTools";
import type { WebMcpContext } from "./webMcpTypes";

export function useWebMcp(state: WebMcpState) {
  const latest = useRef(state);
  const [error, setError] = useState<string | null>(null);
  useLayoutEffect(() => {
    latest.current = state;
  });
  useEffect(() => {
    setError(null);
    const context = (document as Document & { modelContext?: WebMcpContext }).modelContext;
    if (!context) return;
    const controller = new AbortController();
    const current = () => {
      if (controller.signal.aborted) throw new Error("The student session is no longer active.");
      return latest.current;
    };
    const tools = [
      ...createPublicWebMcpTools(current),
      ...(hasStudentWebMcpCredentials(state.session) ? createWebMcpTools(current) : []),
    ];
    async function register() {
      try {
        for (const tool of tools) {
          if (controller.signal.aborted) return;
          await context!.registerTool(tool, { signal: controller.signal });
        }
      } catch {
        if (controller.signal.aborted) return;
        controller.abort();
        setError("WebMCP tools could not be registered. Reload to reconnect your browser agent.");
      }
    }
    void register();
    return () => controller.abort();
  }, [state.session]);
  return error;
}
