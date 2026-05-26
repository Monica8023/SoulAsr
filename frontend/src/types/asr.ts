export interface DebugFormState {
  modelName: string;
  language: string;
  hotwords: string;
  enableItn: boolean;
  pushByRealtime: boolean;
  chunkDurationMs: number;
}

export interface SessionStartPayload {
  type: "start";
  fileName: string;
  modelName: string;
  audioFormat: "file-bytes" | "pcm_s16le";
  sampleRate: number;
  channels: number;
  language: string;
  hotwords: string[];
  enableItn: boolean;
  pushByRealtime: boolean;
}

export interface SessionEndPayload {
  type: "end";
}

export interface TranscriptMessage {
  type: "partial" | "final" | "metrics" | "error" | "ack" | "vad";
  text?: string;
  latencyMs?: number;
  firstTokenMs?: number;
  totalDurationMs?: number;
  rtf?: number;
  detail?: string;
  isFinal?: boolean;
  speechActive?: boolean;
  sentenceIndex?: number;
  shouldTranscribe?: boolean;
}

export interface TaskMetrics {
  rtf: number;
  firstTokenMs: number;
  totalDurationMs: number;
  latencyMs: number;
}
