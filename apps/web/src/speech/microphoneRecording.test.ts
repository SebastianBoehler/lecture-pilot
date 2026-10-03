import { beforeEach, expect, it, vi } from "vitest";
import { startMicrophoneRecording } from "./microphoneRecording";

let stopTrack: ReturnType<typeof vi.fn>;
let context: AudioContext;
let port: {
  onmessage?: (event: { data: unknown }) => void;
  postMessage: ReturnType<typeof vi.fn>;
  close: ReturnType<typeof vi.fn>;
};
let disconnect: ReturnType<typeof vi.fn>;
let abort: AbortController;

beforeEach(() => {
  abort = new AbortController();
  stopTrack = vi.fn();
  disconnect = vi.fn();
  port = { postMessage: vi.fn(() => port.onmessage?.({ data: "stopped" })), close: vi.fn() };
  context = {
    sampleRate: 48_000,
    audioWorklet: { addModule: vi.fn().mockResolvedValue(undefined) },
    createMediaStreamSource: () => ({ connect: vi.fn(), disconnect }),
    destination: {},
    close: vi.fn().mockResolvedValue(undefined),
  } as unknown as AudioContext;
  vi.stubGlobal("navigator", {
    mediaDevices: {
      getUserMedia: vi.fn().mockResolvedValue({ getTracks: () => [{ stop: stopTrack }] }),
    },
  });
  vi.stubGlobal(
    "AudioWorkletNode",
    class {
      port = port;
      connect = vi.fn();
      disconnect = disconnect;
    },
  );
});

it("releases microphone tracks if worklet initialization fails", async () => {
  vi.mocked(context.audioWorklet.addModule).mockRejectedValue(new Error("Worklet unavailable"));
  await expect(startMicrophoneRecording(context, vi.fn(), abort.signal)).rejects.toThrow(
    "Worklet unavailable",
  );
  expect(stopTrack).toHaveBeenCalledTimes(1);
  expect(context.close).toHaveBeenCalled();
});

it("cancels capture without transcribing or leaving microphone tracks running", async () => {
  const recording = await startMicrophoneRecording(context, vi.fn(), abort.signal);
  port.onmessage?.({ data: new Float32Array([0.5]) });
  recording.cancel();
  recording.cancel();
  expect(stopTrack).toHaveBeenCalledTimes(1);
  expect(port.close).toHaveBeenCalledTimes(1);
  expect(context.close).toHaveBeenCalledTimes(1);
});

it("flushes the last audio samples and resamples to 16 kHz after stopping the microphone", async () => {
  const copied: Float32Array[] = [];
  const resampler = vi.fn();
  vi.stubGlobal(
    "OfflineAudioContext",
    class {
      destination = {};
      constructor(...args: unknown[]) {
        resampler(...args);
      }
      createBuffer() {
        return { copyToChannel: (chunk: Float32Array) => copied.push(chunk) };
      }
      createBufferSource() {
        return { connect: vi.fn(), start: vi.fn(), buffer: null };
      }
      async startRendering() {
        return { getChannelData: () => new Float32Array([0.25]) };
      }
    },
  );
  const recording = await startMicrophoneRecording(context, vi.fn(), abort.signal);
  port.onmessage?.({ data: new Float32Array([0.25, 0.5, -0.25]) });
  port.postMessage.mockImplementationOnce(() => {
    expect(stopTrack).toHaveBeenCalled();
    port.onmessage?.({ data: new Float32Array([0.75, 0.5, -0.5]) });
    port.onmessage?.({ data: "stopped" });
  });
  expect(await recording.stop()).toEqual(new Float32Array([0.25]));
  expect(resampler).toHaveBeenCalledWith(1, 2, 16000);
  expect(copied).toHaveLength(2);
  expect(context.close).toHaveBeenCalled();
});

it("reports empty recordings and stops capture at the worklet's sample limit", async () => {
  const limit = vi.fn();
  const recording = await startMicrophoneRecording(context, limit, abort.signal);
  port.onmessage?.({ data: "limit" });
  expect(limit).toHaveBeenCalledTimes(1);
  await expect(recording.stop()).rejects.toThrow("empty");
  expect(stopTrack).toHaveBeenCalled();
});

it("immediately stops acquired tracks when cancellation interrupts worklet initialization", async () => {
  let finish!: () => void;
  vi.mocked(context.audioWorklet.addModule).mockImplementationOnce(
    () =>
      new Promise((resolve) => {
        finish = resolve;
      }),
  );
  const starting = startMicrophoneRecording(context, vi.fn(), abort.signal);
  await Promise.resolve();
  abort.abort();
  expect(stopTrack).toHaveBeenCalledTimes(1);
  finish();
  await expect(starting).rejects.toThrow();
});
