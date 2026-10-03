import type { MicrophoneRecording } from "./whistleTypes";

export async function startMicrophoneRecording(
  context: AudioContext,
  onLimit: () => void,
  signal: AbortSignal,
): Promise<MicrophoneRecording> {
  if (!navigator.mediaDevices?.getUserMedia || !context.audioWorklet) {
    throw new Error("unsupported");
  }
  const stream = await navigator.mediaDevices.getUserMedia({
    audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true },
  });
  let node: AudioWorkletNode | undefined;
  let source: MediaStreamAudioSourceNode | undefined;
  let chunks: Float32Array<ArrayBuffer>[] = [];
  let resolveFlush: (() => void) | undefined;
  let closed = false;
  function abort() {
    chunks = [];
    release();
  }
  function release() {
    if (closed) return;
    closed = true;
    signal.removeEventListener("abort", abort);
    stream.getTracks().forEach((track) => track.stop());
    source?.disconnect();
    if (node) {
      node.disconnect();
      node.port.close();
    }
    void context.close();
    resolveFlush?.();
  }
  signal.addEventListener("abort", abort, { once: true });
  try {
    signal.throwIfAborted();
    await context.audioWorklet.addModule("/speech/pcm-capture.js");
    signal.throwIfAborted();
    source = context.createMediaStreamSource(stream);
    node = new AudioWorkletNode(context, "lecturepilot-pcm-capture");
    node.port.onmessage = ({ data }: MessageEvent<Float32Array<ArrayBuffer> | string>) => {
      if (data instanceof Float32Array) chunks.push(data);
      else if (data === "limit") onLimit();
      else if (data === "stopped") resolveFlush?.();
    };
    source.connect(node);
    node.connect(context.destination); // The worklet emits silence, never microphone audio.
    return {
      async stop() {
        stream.getTracks().forEach((track) => track.stop());
        let rejectFlush!: (cause: Error) => void;
        const flushed = new Promise<void>((resolve, reject) => {
          resolveFlush = resolve;
          rejectFlush = reject;
        });
        node!.port.postMessage("stop");
        const timer = setTimeout(
          () => rejectFlush(new Error("Microphone did not finish recording.")),
          1000,
        );
        try {
          await flushed;
        } finally {
          clearTimeout(timer);
          release();
        }
        const frames = chunks.reduce((sum, chunk) => sum + chunk.length, 0);
        if (!frames) throw new Error("empty");
        const rendering = new OfflineAudioContext(
          1,
          Math.min(480_000, Math.ceil((frames * 16_000) / context.sampleRate)),
          16_000,
        );
        const buffer = rendering.createBuffer(1, frames, context.sampleRate);
        let offset = 0;
        for (const chunk of chunks) {
          buffer.copyToChannel(chunk, 0, offset);
          offset += chunk.length;
        }
        chunks = [];
        const playback = rendering.createBufferSource();
        playback.buffer = buffer;
        playback.connect(rendering.destination);
        playback.start();
        return (await rendering.startRendering()).getChannelData(0);
      },
      cancel() {
        abort();
      },
    };
  } catch (cause) {
    release();
    throw cause;
  }
}
