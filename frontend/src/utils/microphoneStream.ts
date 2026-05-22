const TARGET_SAMPLE_RATE = 16000;
const TARGET_CHANNELS = 1;
const BYTES_PER_SAMPLE = 2;

export interface MicrophoneChunkStats {
  sampleRate: number;
  channels: number;
  sentFrames: number;
  sentSamples: number;
  sentBytes: number;
  durationSeconds: number;
}

export interface MicrophoneStreamOptions {
  frameDurationMs?: number;
  targetSampleRate?: number;
  onChunk: (chunk: ArrayBuffer, stats: MicrophoneChunkStats) => void;
}

export interface MicrophonePcmStreamController {
  readonly sampleRate: number;
  readonly channels: number;
  stop: () => Promise<void>;
}

function getMicAvailabilityError() {
  if (!window.isSecureContext) {
    return "当前页面不是安全上下文，浏览器会禁用麦克风。请使用 https 或 localhost 打开页面。";
  }

  if (!navigator.mediaDevices || typeof navigator.mediaDevices.getUserMedia !== "function") {
    return "当前浏览器不支持麦克风采集，请使用支持 getUserMedia 的现代浏览器。";
  }

  if (typeof window.AudioContext === "undefined") {
    return "当前浏览器不支持 AudioContext，无法进行实时 PCM 推流。";
  }

  return null;
}

function downmixToMono(input: AudioBuffer) {
  if (input.numberOfChannels <= 1) {
    return input.getChannelData(0);
  }

  const reference = input.getChannelData(0);
  const mono = new Float32Array(reference.length);

  for (let channelIndex = 0; channelIndex < input.numberOfChannels; channelIndex += 1) {
    const channel = input.getChannelData(channelIndex);
    for (let sampleIndex = 0; sampleIndex < channel.length; sampleIndex += 1) {
      mono[sampleIndex] += channel[sampleIndex];
    }
  }

  for (let sampleIndex = 0; sampleIndex < mono.length; sampleIndex += 1) {
    mono[sampleIndex] /= input.numberOfChannels;
  }

  return mono;
}

function linearResample(input: Float32Array, sourceRate: number, targetRate: number) {
  if (sourceRate === targetRate) {
    return input;
  }

  const targetLength = Math.floor((input.length * targetRate) / sourceRate);
  if (targetLength <= 0) {
    return new Float32Array(0);
  }

  const resampled = new Float32Array(targetLength);
  const ratio = (input.length - 1) / Math.max(targetLength - 1, 1);

  for (let index = 0; index < targetLength; index += 1) {
    const position = index * ratio;
    const left = Math.floor(position);
    const right = Math.min(left + 1, input.length - 1);
    const weight = position - left;
    resampled[index] = input[left] * (1 - weight) + input[right] * weight;
  }

  return resampled;
}

function floatToPcm16(input: Float32Array) {
  const pcm16 = new Int16Array(input.length);

  for (let index = 0; index < input.length; index += 1) {
    const sample = Math.max(-1, Math.min(1, input[index]));
    pcm16[index] = sample < 0 ? Math.round(sample * 0x8000) : Math.round(sample * 0x7fff);
  }

  return pcm16;
}

function concatPcm16(left: Int16Array, right: Int16Array) {
  const merged = new Int16Array(left.length + right.length);
  merged.set(left, 0);
  merged.set(right, left.length);
  return merged;
}

function toArrayBuffer(chunk: Int16Array) {
  const bytes = new Uint8Array(chunk.byteLength);
  bytes.set(new Uint8Array(chunk.buffer, chunk.byteOffset, chunk.byteLength));
  return bytes.buffer;
}

export async function createMicrophonePcmStream(
  options: MicrophoneStreamOptions,
): Promise<MicrophonePcmStreamController> {
  const availabilityError = getMicAvailabilityError();
  if (availabilityError) {
    throw new Error(availabilityError);
  }

  const targetSampleRate = options.targetSampleRate ?? TARGET_SAMPLE_RATE;
  const frameDurationMs = options.frameDurationMs ?? 60;
  const samplesPerFrame = Math.max(1, Math.floor((targetSampleRate * frameDurationMs) / 1000));

  const mediaStream = await navigator.mediaDevices.getUserMedia({
    audio: {
      channelCount: TARGET_CHANNELS,
      echoCancellation: false,
      noiseSuppression: false,
      autoGainControl: false,
    },
    video: false,
  });

  const audioContext = new AudioContext();
  const source = audioContext.createMediaStreamSource(mediaStream);
  const processor = audioContext.createScriptProcessor(4096, source.channelCount, TARGET_CHANNELS);

  let bufferedPcm = new Int16Array(0);
  let stopped = false;
  let sentFrames = 0;
  let sentSamples = 0;

  const emitChunk = (chunk: Int16Array) => {
    if (!chunk.length) {
      return;
    }

    sentFrames += 1;
    sentSamples += chunk.length;
    options.onChunk(toArrayBuffer(chunk), {
      sampleRate: targetSampleRate,
      channels: TARGET_CHANNELS,
      sentFrames,
      sentSamples,
      sentBytes: sentSamples * BYTES_PER_SAMPLE,
      durationSeconds: sentSamples / targetSampleRate,
    });
  };

  processor.onaudioprocess = (event) => {
    if (stopped) {
      return;
    }

    const mono = downmixToMono(event.inputBuffer);
    const resampled = linearResample(mono, audioContext.sampleRate, targetSampleRate);
    const pcm16 = floatToPcm16(resampled);
    bufferedPcm = concatPcm16(bufferedPcm, pcm16);

    while (bufferedPcm.length >= samplesPerFrame) {
      emitChunk(bufferedPcm.slice(0, samplesPerFrame));
      bufferedPcm = bufferedPcm.slice(samplesPerFrame);
    }
  };

  source.connect(processor);
  processor.connect(audioContext.destination);

  const stop = async () => {
    if (stopped) {
      return;
    }

    stopped = true;

    if (bufferedPcm.length > 0) {
      emitChunk(bufferedPcm);
      bufferedPcm = new Int16Array(0);
    }

    processor.disconnect();
    source.disconnect();
    processor.onaudioprocess = null;
    mediaStream.getTracks().forEach((track) => track.stop());

    if (audioContext.state !== "closed") {
      await audioContext.close();
    }
  };

  return {
    sampleRate: targetSampleRate,
    channels: TARGET_CHANNELS,
    stop,
  };
}
