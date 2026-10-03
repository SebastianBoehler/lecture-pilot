class PcmCapture extends AudioWorkletProcessor {
  constructor() {
    super();
    this.buffer = new Float32Array(4096);
    this.offset = 0;
    this.samples = 0;
    this.stopped = false;
    this.port.onmessage = () => {
      this.stopped = true;
      this.flush();
      this.port.postMessage("stopped");
    };
  }

  flush() {
    if (!this.offset) return;
    const chunk = this.buffer.slice(0, this.offset);
    this.port.postMessage(chunk, [chunk.buffer]);
    this.offset = 0;
  }

  process(inputs) {
    if (this.stopped) return false;
    const channel = inputs[0]?.[0];
    if (!channel) return true;
    for (const value of channel) {
      if (this.samples >= sampleRate * 30) {
        this.stopped = true;
        this.flush();
        this.port.postMessage("limit");
        return false;
      }
      this.buffer[this.offset++] = value;
      this.samples++;
      if (this.offset === this.buffer.length) this.flush();
    }
    return true;
  }
}

registerProcessor("lecturepilot-pcm-capture", PcmCapture);
