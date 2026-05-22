const TARGET_SAMPLE_RATE = 16000;
const TARGET_CHANNELS = 1;

export interface PcmAudioData {
  pcm16: Int16Array;
  sampleRate: number;
  channels: number;
  durationSeconds: number;
}

function convertFloatToPcm16(samples: Float32Array) {
  const pcm16 = new Int16Array(samples.length);
  for (let index = 0; index < samples.length; index += 1) {
    const sample = Math.max(-1, Math.min(1, samples[index]));
    pcm16[index] = sample < 0 ? sample * 0x8000 : sample * 0x7fff;
  }
  return pcm16;
}

async function decodeFileToAudioBuffer(file: File) {
  const context = new AudioContext();
  try {
    const arrayBuffer = await file.arrayBuffer();
    return await context.decodeAudioData(arrayBuffer.slice(0));
  } finally {
    await context.close();
  }
}

async function resampleToMono16k(sourceBuffer: AudioBuffer) {
  const frameCount = Math.ceil(sourceBuffer.duration * TARGET_SAMPLE_RATE);
  const offlineContext = new OfflineAudioContext(
    TARGET_CHANNELS,
    Math.max(frameCount, 1),
    TARGET_SAMPLE_RATE,
  );

  const monoBuffer = offlineContext.createBuffer(
    TARGET_CHANNELS,
    sourceBuffer.length,
    sourceBuffer.sampleRate,
  );

  const monoData = monoBuffer.getChannelData(0);
  for (let channelIndex = 0; channelIndex < sourceBuffer.numberOfChannels; channelIndex += 1) {
    const channelData = sourceBuffer.getChannelData(channelIndex);
    for (let sampleIndex = 0; sampleIndex < channelData.length; sampleIndex += 1) {
      monoData[sampleIndex] += channelData[sampleIndex] / sourceBuffer.numberOfChannels;
    }
  }

  const source = offlineContext.createBufferSource();
  source.buffer = monoBuffer;
  source.connect(offlineContext.destination);
  source.start(0);

  return offlineContext.startRendering();
}

export async function fileToPcm16Stream(file: File): Promise<PcmAudioData> {
  const decodedBuffer = await decodeFileToAudioBuffer(file);
  const mono16kBuffer = await resampleToMono16k(decodedBuffer);
  const monoSamples = mono16kBuffer.getChannelData(0);
  const pcm16 = convertFloatToPcm16(monoSamples);

  return {
    pcm16,
    sampleRate: TARGET_SAMPLE_RATE,
    channels: TARGET_CHANNELS,
    durationSeconds: mono16kBuffer.duration,
  };
}

export function pcm16ToByteChunks(
  pcm16: Int16Array,
  chunkDurationMs = 60,
  sampleRate = TARGET_SAMPLE_RATE,
  channels = TARGET_CHANNELS,
) {
  const samplesPerChunk = Math.max(
    1,
    Math.floor((sampleRate * channels * chunkDurationMs) / 1000),
  );
  const chunks: ArrayBuffer[] = [];

  for (let offset = 0; offset < pcm16.length; offset += samplesPerChunk) {
    const chunk = pcm16.slice(offset, Math.min(offset + samplesPerChunk, pcm16.length));
    chunks.push(chunk.buffer.slice(0));
  }

  return chunks;
}
