export type SpeechLanguage = "en" | "de";
export type SpeechState = "idle" | "loading" | "requesting" | "recording" | "transcribing";

export type WhistleRequest =
  | { id: number; type: "load" }
  | { id: number; type: "transcribe"; pcm: Float32Array; language: SpeechLanguage };
export type WhistleReply = { id: number; text?: string; error?: string };

export interface WhistleModule {
  HEAPU8: Uint8Array;
  _malloc(bytes: number): number;
  _free(pointer: number): void;
  _needle_load(pointer: number, size: bigint): number;
  _needle_models(): number;
  _needle_last_error(): number;
  _needle_transcribe(
    pcm: number,
    samples: number,
    language: number,
    keywords: number,
    timestamps: number,
    output: number,
    capacity: number,
  ): number;
  UTF8ToString(pointer: number): string;
}

export interface MicrophoneRecording {
  stop(): Promise<Float32Array>;
  cancel(): void;
}
