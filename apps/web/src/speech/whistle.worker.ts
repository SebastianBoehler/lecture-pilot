import assets from "./whistleAssets.json";
import { transcribePcm } from "./whistleInference";
import type { WhistleModule, WhistleRequest, WhistleReply } from "./whistleTypes";

const scope = self as unknown as {
  onmessage: (event: MessageEvent<WhistleRequest>) => void;
  postMessage(reply: WhistleReply): void;
};
let runtime: Promise<WhistleModule> | undefined;

async function loadRuntime() {
  const base = `/speech/${assets.directory}`;
  // An absolute URL keeps Vite from transforming the pinned public module.
  const moduleUrl = new URL(`${base}/needle.mjs`, self.location.origin).href;
  const [{ default: createNeedle }, wasm, weights] = await Promise.all([
    import(/* @vite-ignore */ moduleUrl),
    fetchBytes(`${base}/needle.wasm`),
    fetchBytes(`${base}/whistle.cact`),
  ]);
  const module: WhistleModule = await createNeedle({ wasmBinary: wasm });
  const pointer = module._malloc(weights.byteLength);
  if (!pointer) throw new Error("Whistle could not allocate model memory.");
  try {
    module.HEAPU8.set(weights, pointer);
    if (module._needle_load(pointer, BigInt(weights.byteLength)) < 0) {
      throw new Error(module.UTF8ToString(module._needle_last_error()));
    }
    if (module._needle_models() !== 2) throw new Error("Whistle speech model did not load.");
  } finally {
    module._free(pointer);
  }
  return module;
}

async function fetchBytes(url: string) {
  const response = await fetch(url, { signal: AbortSignal.timeout(120_000) });
  if (!response.ok) throw new Error(`Whistle could not load ${url}: HTTP ${response.status}`);
  return new Uint8Array(await response.arrayBuffer());
}

scope.onmessage = async ({ data }) => {
  try {
    runtime ??= loadRuntime();
    const module = await runtime;
    const text =
      data.type === "transcribe" ? transcribePcm(module, data.pcm, data.language) : undefined;
    scope.postMessage({ id: data.id, text });
  } catch (cause) {
    runtime = undefined;
    scope.postMessage({
      id: data.id,
      error: cause instanceof Error ? cause.message : "Whistle failed.",
    });
  }
};
