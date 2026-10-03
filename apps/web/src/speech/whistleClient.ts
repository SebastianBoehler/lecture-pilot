import type { SpeechLanguage, WhistleReply, WhistleRequest } from "./whistleTypes";

export class WhistleClient {
  private worker = new Worker(new URL("./whistle.worker.ts", import.meta.url), { type: "module" });
  private nextId = 0;
  private requests = new Map<number, { resolve(text: string): void; reject(cause: Error): void }>();
  private loaded: Promise<void> | undefined;
  private disposed = false;

  constructor() {
    this.worker.onmessage = ({ data }: MessageEvent<WhistleReply>) => {
      const request = this.requests.get(data.id);
      if (!request) return;
      this.requests.delete(data.id);
      if (data.error) request.reject(new Error(data.error));
      else request.resolve(data.text ?? "");
    };
    this.worker.onerror = () => this.dispose();
    this.worker.onmessageerror = () => this.dispose();
  }

  load() {
    if (this.disposed) return Promise.reject(new Error("Whistle worker stopped."));
    this.loaded ??= this.request({ id: ++this.nextId, type: "load" }).then(() => undefined);
    return this.loaded;
  }

  transcribe(pcm: Float32Array, language: SpeechLanguage) {
    return this.request({ id: ++this.nextId, type: "transcribe", pcm, language });
  }

  dispose() {
    this.disposed = true;
    this.worker.terminate();
    for (const request of this.requests.values())
      request.reject(new Error("Whistle worker stopped."));
    this.requests.clear();
  }

  private request(message: WhistleRequest) {
    if (this.disposed) return Promise.reject(new Error("Whistle worker stopped."));
    return new Promise<string>((resolve, reject) => {
      const timer = setTimeout(() => {
        reject(new Error("Whistle timed out. Please try again."));
        this.dispose();
      }, 120_000);
      this.requests.set(message.id, {
        resolve: (text) => {
          clearTimeout(timer);
          resolve(text);
        },
        reject: (cause) => {
          clearTimeout(timer);
          reject(cause);
        },
      });
      this.worker.postMessage(message, message.type === "transcribe" ? [message.pcm.buffer] : []);
    });
  }
}
