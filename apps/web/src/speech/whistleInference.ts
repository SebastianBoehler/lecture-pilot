import type { SpeechLanguage, WhistleModule } from "./whistleTypes";

const SAMPLE_RATE = 16_000;
const OUTPUT_BYTES = 32_768;

export function transcribePcm(module: WhistleModule, pcm: Float32Array, language: SpeechLanguage) {
  if (
    !pcm.length ||
    pcm.length > SAMPLE_RATE * 30 ||
    pcm.some((sample) => !Number.isFinite(sample))
  ) {
    throw new Error("Whistle requires a finite audio clip of up to 30 seconds.");
  }
  if (language !== "en" && language !== "de") throw new Error("Unsupported speech language.");
  const pointers: number[] = [];
  function allocate(bytes: number) {
    const pointer = module._malloc(bytes);
    if (!pointer) throw new Error("Whistle could not allocate audio memory.");
    pointers.push(pointer);
    return pointer;
  }
  try {
    const input = allocate(pcm.byteLength);
    const lang = allocate(3);
    const output = allocate(OUTPUT_BYTES);
    // Allocations can grow WASM memory; copy only after all allocations.
    new Float32Array(module.HEAPU8.buffer).set(pcm, input / 4);
    module.HEAPU8.set([language.charCodeAt(0), language.charCodeAt(1), 0], lang);
    const result = module._needle_transcribe(input, pcm.length, lang, 0, 0, output, OUTPUT_BYTES);
    if (result < 0) throw new Error(module.UTF8ToString(module._needle_last_error()));
    const parsed: unknown = JSON.parse(module.UTF8ToString(output));
    if (
      !parsed ||
      typeof parsed !== "object" ||
      !("text" in parsed) ||
      typeof parsed.text !== "string"
    ) {
      throw new Error("Whistle returned an invalid transcript.");
    }
    return parsed.text.trim();
  } finally {
    pointers.forEach((pointer) => module._free(pointer));
  }
}
