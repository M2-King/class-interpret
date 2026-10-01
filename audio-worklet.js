class ClassInterpreterCapture extends AudioWorkletProcessor {
  constructor() {
    super();
    this.buffer = new Float32Array(2048);
    this.offset = 0;
    this.port.onmessage = event => {
      if (event.data === 'flush' && this.offset) this.emit();
    };
  }

  emit() {
    const chunk = this.buffer.slice(0, this.offset);
    this.port.postMessage(chunk, [chunk.buffer]);
    this.offset = 0;
  }

  process(inputs) {
    const input = inputs[0]?.[0];
    if (!input) return true;
    let cursor = 0;
    while (cursor < input.length) {
      const amount = Math.min(input.length - cursor, this.buffer.length - this.offset);
      this.buffer.set(input.subarray(cursor, cursor + amount), this.offset);
      this.offset += amount;
      cursor += amount;
      if (this.offset === this.buffer.length) this.emit();
    }
    return true;
  }
}

registerProcessor('class-interpreter-capture', ClassInterpreterCapture);
