import { beforeEach, expect, it, vi } from "vitest";
import { transcribePcm } from "./whistleInference";
import type { WhistleModule } from "./whistleTypes";

let heap: ArrayBuffer;
let nextPointer: number;
let module: WhistleModule;

beforeEach(() => {
  heap = new ArrayBuffer(100_000);
  nextPointer = 8;
  module = {
    HEAPU8: new Uint8Array(heap),
    _malloc: vi.fn((bytes) => {
      const pointer = nextPointer;
      nextPointer += Math.ceil(bytes / 8) * 8;
      return pointer;
    }),
    _free: vi.fn(),
    _needle_load: vi.fn(),
    _needle_models: vi.fn(),
    _needle_last_error: () => 4,
    _needle_transcribe: vi.fn(() => 5),
    UTF8ToString: vi.fn(() => JSON.stringify({ text: "  Eine Frage.  " })),
  };
});

it("passes mono PCM and an explicit German language to the native API", () => {
  const pcm = new Float32Array([0.25, -0.5]);
  expect(transcribePcm(module, pcm, "de")).toBe("Eine Frage.");
  const [input, count, lang, keywords, timestamps, output, capacity] = vi.mocked(
    module._needle_transcribe,
  ).mock.calls[0];
  expect(count).toBe(2);
  expect(new Float32Array(module.HEAPU8.buffer).slice(input / 4, input / 4 + 2)).toEqual(pcm);
  expect(module.HEAPU8.slice(lang, lang + 3)).toEqual(new Uint8Array([100, 101, 0]));
  expect([keywords, timestamps, capacity]).toEqual([0, 0, 32768]);
  expect(vi.mocked(module._free).mock.calls.flat()).toEqual([input, lang, output]);
});

it("copies audio into the current memory view after allocations grow the heap", () => {
  vi.mocked(module._malloc).mockImplementation((bytes) => {
    const pointer = nextPointer;
    nextPointer += Math.ceil(bytes / 8) * 8;
    const replacement = new Uint8Array(100_000);
    replacement.set(module.HEAPU8);
    module.HEAPU8 = replacement;
    return pointer;
  });
  transcribePcm(module, new Float32Array([0.75]), "en");
  expect(new Float32Array(module.HEAPU8.buffer)[2]).toBe(0.75);
});

it.each([new Float32Array(), new Float32Array(480001), new Float32Array([NaN])])(
  "rejects invalid clips before invoking native code",
  (pcm) => {
    expect(() => transcribePcm(module, pcm, "en")).toThrow("up to 30 seconds");
    expect(module._needle_transcribe).not.toHaveBeenCalled();
  },
);

it("frees native memory on invalid provider output", () => {
  vi.mocked(module.UTF8ToString).mockReturnValue('{"text": false}');
  expect(() => transcribePcm(module, new Float32Array([0]), "en")).toThrow("invalid transcript");
  expect(module._free).toHaveBeenCalledTimes(3);
});

it("reports the native error and frees partially allocated memory", () => {
  vi.mocked(module._needle_transcribe).mockReturnValue(-1);
  vi.mocked(module.UTF8ToString).mockReturnValue("Audio decoding failed");
  expect(() => transcribePcm(module, new Float32Array([0]), "en")).toThrow("Audio decoding failed");
  expect(module._free).toHaveBeenCalledTimes(3);
  vi.mocked(module._malloc).mockReturnValueOnce(8).mockReturnValueOnce(0);
  expect(() => transcribePcm(module, new Float32Array([0]), "en")).toThrow("allocate audio memory");
  expect(module._free).toHaveBeenLastCalledWith(8);
});
