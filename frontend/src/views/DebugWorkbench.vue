<template>
  <section class="page-stack">
    <div class="page-lead">
      <div>
        <h2>ASR 实时调试工作台</h2>
        <p>
          实时识别已切换为浏览器麦克风 PCM 推流模式。上传文件仅用于波形预览和离线调试辅助，不再作为实时流输入源。
        </p>
      </div>
      <div class="lead-tags">
        <el-tag :type="statusTagType" effect="dark" round class="socket-tag">
          Socket: {{ socketStatus }}
        </el-tag>
        <el-tag effect="dark" round class="socket-tag" :type="streamTagType">
          Mic: {{ microphoneLabel }}
        </el-tag>
      </div>
    </div>

    <el-card class="panel workbench-panel" :class="{ 'active-module': streaming }" shadow="never">
      <template #header>
        <div class="panel-header">
          <div>
            <h3>输入与控制区</h3>
            <p>实时推流固定发送 16kHz、单声道、PCM16 数据，便于直接对接后端 VAD 与流式识别链路。</p>
          </div>
          <div class="control-actions">
            <el-button
              @click="disconnectSocket"
              :disabled="socketStatus === 'idle' || socketStatus === 'closed'"
            >
              断开连接
            </el-button>
            <el-button
              type="danger"
              plain
              @click="stopRecognition"
              :disabled="!streaming && microphoneState !== 'stopping'"
            >
              停止识别
            </el-button>
            <el-button
              type="primary"
              :loading="microphoneState === 'starting'"
              :disabled="streaming || microphoneState === 'stopping'"
              @click="startRecognition"
            >
              {{ streaming ? "麦克风推流中..." : "开始麦克风实时识别" }}
            </el-button>
          </div>
        </div>
      </template>

      <div class="control-stack">
        <el-upload
          class="upload-panel"
          drag
          :auto-upload="false"
          :show-file-list="false"
          accept="audio/*"
          :on-change="handleFileChange"
        >
          <el-icon class="upload-icon"><UploadFilled /></el-icon>
          <div class="el-upload__text">拖拽音频到此处，或 <em>点击选择文件</em></div>
          <template #tip>
            <div class="el-upload__tip">
              {{
                selectedFile
                  ? `已选择：${selectedFile.name}，仅用于预览波形，不参与实时推流`
                  : "支持常见桌面音频文件格式，仅用于预览波形"
              }}
            </div>
          </template>
        </el-upload>

        <WaveformPlayer :file="selectedFile" :vad-segments="demoVadSegments" @ready="handleWaveReady" />

        <div class="stream-status-grid">
          <div class="status-card">
            <span>实时输入</span>
            <strong>Browser Mic / PCM16</strong>
          </div>
          <div class="status-card">
            <span>VAD 状态</span>
            <strong class="vad-state-line">
              <i class="vad-dot" :class="{ active: vadSpeechActive }"></i>
              {{ vadSpeechActive ? "Speaking" : "Silence" }}
            </strong>
          </div>
          <div class="status-card">
            <span>采样规格</span>
            <strong>16kHz / Mono</strong>
          </div>
          <div class="status-card">
            <span>已发送帧数</span>
            <strong>{{ sentFrames }}</strong>
          </div>
          <div class="status-card">
            <span>已发送音频</span>
            <strong>{{ realtimeAudioSeconds.toFixed(2) }} s</strong>
          </div>
          <div class="status-card">
            <span>句尾次数</span>
            <strong>{{ sentenceCount }}</strong>
          </div>
          <div class="status-card">
            <span>最近句尾</span>
            <strong>{{ lastSentenceAt }}</strong>
          </div>
        </div>

        <div class="vad-event-strip">
          <div class="vad-strip-title">VAD 事件</div>
          <div class="vad-event-list">
            <span v-if="vadEventLogs.length === 0" class="vad-event-empty">等待语音活动...</span>
            <span v-for="(event, index) in vadEventLogs" :key="`${event}-${index}`" class="vad-event-chip">
              {{ event }}
            </span>
          </div>
        </div>

        <div class="param-grid">
          <el-form label-position="top" class="param-form">
            <el-form-item label="模型选择">
              <el-select v-model="form.modelName" placeholder="选择模型">
                <el-option label="zipformer" value="zipformer" />
                <el-option label="paraformer" value="paraformer" />
                <el-option label="qwen3-asr" value="qwen3-asr" />
                <el-option label="funasr" value="funasr" />
                <el-option label="whisper" value="whisper" />
              </el-select>
            </el-form-item>

            <el-form-item label="目标语言">
              <el-select v-model="form.language" placeholder="选择语言">
                <el-option label="中文" value="zh" />
                <el-option label="英文" value="en" />
                <el-option label="自动检测" value="auto" />
              </el-select>
            </el-form-item>

            <el-form-item label="热词注入">
              <el-input
                v-model="form.hotwords"
                placeholder="多个热词用逗号分隔"
                clearable
              />
            </el-form-item>

            <el-form-item label="ITN 开关">
              <el-switch v-model="form.enableItn" />
            </el-form-item>

            <el-form-item label="推流分帧">
              <el-input-number
                v-model="form.chunkDurationMs"
                :min="20"
                :max="200"
                :step="10"
                controls-position="right"
              />
            </el-form-item>

            <el-form-item label="上传文件时长">
              <div class="inline-note">
                {{ selectedFile ? `${previewAudioDuration.toFixed(2)} s` : "未选择文件" }}
              </div>
            </el-form-item>

            <el-form-item label="推流模式">
              <div class="inline-note">浏览器麦克风实时采集，发送固定 16k 单声道 PCM</div>
            </el-form-item>
          </el-form>
        </div>
      </div>
    </el-card>

    <div class="two-columns">
      <el-card class="panel" shadow="never">
        <template #header>
          <div class="panel-header">
            <div>
              <h3>转写面板</h3>
              <p>区分最终文本与临时结果，便于观察流式刷新过程。</p>
            </div>
          </div>
        </template>

        <div class="transcript-stream">
          <div v-if="finalSegments.length === 0" class="empty-state">等待识别结果...</div>
          <p v-for="(segment, index) in finalSegments" :key="`${segment}-${index}`" class="final-segment">
            {{ segment }}
          </p>
          <p v-if="partialText" class="partial-segment">{{ partialText }}</p>
        </div>

        <div v-if="errorLogs.length > 0" class="error-log">
          <strong>错误日志</strong>
          <p v-for="(log, index) in errorLogs" :key="`${log}-${index}`">{{ log }}</p>
        </div>
      </el-card>

      <el-card class="panel" shadow="never">
        <template #header>
          <div class="panel-header">
            <div>
              <h3>性能数据</h3>
              <p>关键指标和原始报文按任务维度归档。</p>
            </div>
          </div>
        </template>

        <el-descriptions :column="1" border class="metrics-board">
          <el-descriptions-item label="RTF"><span class="numeric">{{ metrics.rtf.toFixed(2) }}</span></el-descriptions-item>
          <el-descriptions-item label="首字延迟"><span class="numeric">{{ metrics.firstTokenMs }} ms</span></el-descriptions-item>
          <el-descriptions-item label="总耗时"><span class="numeric">{{ metrics.totalDurationMs }} ms</span></el-descriptions-item>
          <el-descriptions-item label="处理延迟"><span class="numeric">{{ metrics.latencyMs }} ms</span></el-descriptions-item>
          <el-descriptions-item label="已发送音频"><span class="numeric">{{ realtimeAudioSeconds.toFixed(2) }} s</span></el-descriptions-item>
          <el-descriptions-item label="已发送字节"><span class="numeric">{{ sentBytes }}</span></el-descriptions-item>
        </el-descriptions>

        <el-collapse class="raw-preview">
          <el-collapse-item title="原始 JSON 报文预览" name="payloads">
            <pre class="code-preview">{{ rawMessagePreview }}</pre>
          </el-collapse-item>
        </el-collapse>
      </el-card>
    </div>
  </section>
</template>

<script setup lang="ts">
import { UploadFilled } from "@element-plus/icons-vue";
import { ElMessage, type UploadFile } from "element-plus";
import { computed, onBeforeUnmount, reactive, ref, shallowRef } from "vue";

import WaveformPlayer from "../components/WaveformPlayer.vue";
import { useWebSocket } from "../composables/useWebSocket";
import type { DebugFormState, SessionEndPayload, SessionStartPayload, TaskMetrics, TranscriptMessage } from "../types/asr";
import type { MicrophoneChunkStats, MicrophonePcmStreamController } from "../utils/microphoneStream";
import { createMicrophonePcmStream } from "../utils/microphoneStream";

const form = reactive<DebugFormState>({
  modelName: "zipformer",
  language: "zh",
  hotwords: "",
  enableItn: true,
  pushByRealtime: true,
  chunkDurationMs: 60,
});

const selectedFile = ref<File | null>(null);
const partialText = ref("");
const finalSegments = ref<string[]>([]);
const rawMessages = ref<string[]>([]);
const errorLogs = ref<string[]>([]);
const previewAudioDuration = ref(0);
const realtimeAudioSeconds = ref(0);
const sentFrames = ref(0);
const sentBytes = ref(0);
const streaming = ref(false);
const microphoneState = ref<"idle" | "starting" | "streaming" | "stopping">("idle");
const microphoneStream = shallowRef<MicrophonePcmStreamController | null>(null);
const vadSpeechActive = ref(false);
const sentenceCount = ref(0);
const lastSentenceAt = ref("--");
const vadEventLogs = ref<string[]>([]);
const metrics = reactive<TaskMetrics>({
  rtf: 0,
  firstTokenMs: 0,
  totalDurationMs: 0,
  latencyMs: 0,
});

const demoVadSegments = ref([
  { start: 0.4, end: 1.8 },
  { start: 2.4, end: 4.1 },
]);

const socketUrl = computed(() => import.meta.env.VITE_ASR_WS_URL || "ws://localhost:8000/ws/asr");

const parseHotwords = () =>
  form.hotwords
    .split(/[,\n，]/)
    .map((item) => item.trim())
    .filter(Boolean);

const appendVadEvent = (label: string) => {
  const timestamp = new Date().toLocaleTimeString("zh-CN", { hour12: false });
  vadEventLogs.value.unshift(`${timestamp} ${label}`);
  vadEventLogs.value = vadEventLogs.value.slice(0, 8);
};

const resetOutputs = () => {
  partialText.value = "";
  finalSegments.value = [];
  rawMessages.value = [];
  errorLogs.value = [];
  metrics.rtf = 0;
  metrics.firstTokenMs = 0;
  metrics.totalDurationMs = 0;
  metrics.latencyMs = 0;
  realtimeAudioSeconds.value = 0;
  sentFrames.value = 0;
  sentBytes.value = 0;
  vadSpeechActive.value = false;
  sentenceCount.value = 0;
  lastSentenceAt.value = "--";
  vadEventLogs.value = [];
};

const handleSocketMessage = (event: MessageEvent<string | ArrayBuffer>) => {
  if (typeof event.data !== "string") {
    rawMessages.value.push(JSON.stringify({ type: "binary", bytes: event.data.byteLength }));
    return;
  }

  rawMessages.value.push(event.data);

  let message: TranscriptMessage;
  try {
    message = JSON.parse(event.data) as TranscriptMessage;
  } catch {
    return;
  }

  const payload = message as TranscriptMessage & Record<string, unknown>;
  const speechActive =
    typeof payload.speechActive === "boolean"
      ? payload.speechActive
      : typeof payload.speech_active === "boolean"
        ? (payload.speech_active as boolean)
        : undefined;
  const sentenceIndex =
    typeof payload.sentenceIndex === "number"
      ? payload.sentenceIndex
      : typeof payload.sentence_index === "number"
        ? (payload.sentence_index as number)
        : undefined;
  const isSentenceFinal =
    typeof payload.isFinal === "boolean"
      ? payload.isFinal
      : typeof payload.is_final === "boolean"
        ? (payload.is_final as boolean)
        : false;

  if (typeof speechActive === "boolean") {
    vadSpeechActive.value = speechActive;
  }

  if (message.type === "vad") {
    if (speechActive) {
      appendVadEvent("检测到说话");
    } else {
      appendVadEvent(isSentenceFinal ? `句尾触发 #${sentenceIndex || sentenceCount.value + 1}` : "进入静音");
    }
    if (isSentenceFinal) {
      sentenceCount.value = sentenceIndex || sentenceCount.value + 1;
      lastSentenceAt.value = new Date().toLocaleTimeString("zh-CN", { hour12: false });
    }
    return;
  }

  if (message.type === "partial") {
    partialText.value = message.text || "";
  }

  if (message.type === "final") {
    if (message.text) {
      finalSegments.value.push(message.text);
    }
    partialText.value = "";
    if (isSentenceFinal) {
      sentenceCount.value = sentenceIndex || sentenceCount.value;
      lastSentenceAt.value = new Date().toLocaleTimeString("zh-CN", { hour12: false });
    }
  }

  if (message.type === "metrics") {
    metrics.rtf = Number(payload.rtf ?? 0);
    metrics.firstTokenMs = Number(payload.firstTokenMs ?? payload.first_token_ms ?? 0);
    metrics.totalDurationMs = Number(payload.totalDurationMs ?? payload.total_duration_ms ?? 0);
    metrics.latencyMs = Number(payload.latencyMs ?? payload.latency_ms ?? 0);
  }

  if (message.type === "error") {
    errorLogs.value.push(message.detail || "未知错误");
  }
};

const cleanupMicrophone = async () => {
  const controller = microphoneStream.value;
  microphoneStream.value = null;

  if (controller) {
    await controller.stop();
  }
};

const appendErrorLog = (detail: string) => {
  errorLogs.value.push(detail);
};

const updateRealtimeStats = (stats: MicrophoneChunkStats) => {
  realtimeAudioSeconds.value = stats.durationSeconds;
  sentFrames.value = stats.sentFrames;
  sentBytes.value = stats.sentBytes;
};

const { status, errorMessage, connect, send, sendJson, close } = useWebSocket({
  url: socketUrl.value,
  autoReconnect: false,
  reconnectInterval: 2500,
  maxReconnectAttempts: 3,
  onMessage: handleSocketMessage,
  onError: () => {
    appendErrorLog("WebSocket 连接失败，请检查后端实时服务。");
  },
  onClose: (event) => {
    streaming.value = false;
    if (microphoneState.value !== "idle") {
      microphoneState.value = "idle";
    }
    if (microphoneStream.value) {
      void cleanupMicrophone();
    }
    if (event.code !== 1000 && event.reason) {
      appendErrorLog(`连接已关闭：${event.reason}`);
    }
  },
});

const socketStatus = computed(() => status.value);
const statusTagType = computed(() => {
  if (socketStatus.value === "open") return "success";
  if (socketStatus.value === "connecting") return "warning";
  if (socketStatus.value === "error") return "danger";
  return "info";
});
const streamTagType = computed(() => {
  if (microphoneState.value === "streaming") return "success";
  if (microphoneState.value === "starting") return "warning";
  if (microphoneState.value === "stopping") return "danger";
  return "info";
});
const microphoneLabel = computed(() => {
  if (microphoneState.value === "starting") return "requesting";
  if (microphoneState.value === "streaming") return "live";
  if (microphoneState.value === "stopping") return "stopping";
  return "idle";
});

const rawMessagePreview = computed(() => rawMessages.value.join("\n\n") || "暂无原始报文");

const handleFileChange = (uploadFile: UploadFile) => {
  if (!uploadFile.raw) {
    return;
  }
  selectedFile.value = uploadFile.raw;
};

const handleWaveReady = (duration: number) => {
  previewAudioDuration.value = duration;
};

const startRecognition = async () => {
  if (streaming.value || microphoneState.value === "starting") {
    return;
  }

  streaming.value = true;
  microphoneState.value = "starting";
  resetOutputs();

  try {
    if (socketStatus.value !== "open") {
      await connect();
    }

    const startPayload: SessionStartPayload = {
      type: "start",
      fileName: selectedFile.value?.name || "browser-microphone.pcm",
      modelName: form.modelName,
      audioFormat: "pcm_s16le",
      sampleRate: 16000,
      channels: 1,
      language: form.language,
      hotwords: parseHotwords(),
      enableItn: form.enableItn,
      pushByRealtime: form.pushByRealtime,
    };

    sendJson(startPayload);
    microphoneStream.value = await createMicrophonePcmStream({
      frameDurationMs: form.chunkDurationMs,
      onChunk: (chunk, stats) => {
        if (!streaming.value) {
          return;
        }

        try {
          send(chunk);
          updateRealtimeStats(stats);
        } catch (error) {
          const detail = error instanceof Error ? error.message : "实时音频发送失败";
          appendErrorLog(detail);
          void stopRecognition(true);
        }
      },
    });
    microphoneState.value = "streaming";
    ElMessage.success("麦克风已接入，正在实时推流。");
  } catch (error) {
    const detail =
      error instanceof Error ? error.message : errorMessage.value || "实时识别启动失败";
    appendErrorLog(detail);
    await cleanupMicrophone();
    if (socketStatus.value === "open") {
      try {
        const endPayload: SessionEndPayload = { type: "end" };
        sendJson(endPayload);
        close(1000, "startup failed");
      } catch {
        close(1000, "startup failed");
      }
    }
    streaming.value = false;
    microphoneState.value = "idle";
  }
};

const stopRecognition = async (closeSocketAfterStop = false) => {
  if (!streaming.value && microphoneState.value === "idle" && !microphoneStream.value) {
    return;
  }

  streaming.value = false;
  microphoneState.value = "stopping";

  try {
    await cleanupMicrophone();
  } finally {
    if (socketStatus.value === "open") {
      try {
        const endPayload: SessionEndPayload = { type: "end" };
        sendJson(endPayload);
      } catch (error) {
        const detail = error instanceof Error ? error.message : "结束实时识别失败";
        appendErrorLog(detail);
      }
    }

    if (closeSocketAfterStop && socketStatus.value === "open") {
      close(1000, "stream stopped");
    }

    if (socketStatus.value !== "open") {
      microphoneState.value = "idle";
    }
  }
};

const disconnectSocket = async () => {
  await stopRecognition();
  close(1000, "manual close");
};

onBeforeUnmount(() => {
  void cleanupMicrophone();
});
</script>

<style scoped>
.lead-tags {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.control-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.socket-tag {
  box-shadow: 0 0 18px rgba(0, 240, 255, 0.14);
}

.control-stack {
  display: grid;
  gap: 18px;
}

.stream-status-grid {
  display: grid;
  gap: 14px;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.status-card {
  display: grid;
  gap: 6px;
  padding: 16px 18px;
  border-radius: 18px;
  border: 1px solid rgba(0, 240, 255, 0.12);
  background:
    linear-gradient(180deg, rgba(15, 23, 42, 0.54), rgba(30, 41, 59, 0.32)),
    radial-gradient(circle at top left, rgba(0, 240, 255, 0.08), transparent 36%);
}

.status-card span {
  color: #94a3b8;
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.status-card strong {
  color: #f8fafc;
  font-family: var(--mono-font);
  font-size: 15px;
}

.vad-state-line {
  display: inline-flex;
  align-items: center;
  gap: 10px;
}

.vad-dot {
  width: 10px;
  height: 10px;
  border-radius: 999px;
  background: rgba(148, 163, 184, 0.8);
  box-shadow: 0 0 0 rgba(148, 163, 184, 0);
  transition: background-color 160ms ease, box-shadow 160ms ease;
}

.vad-dot.active {
  background: #22c55e;
  box-shadow: 0 0 14px rgba(34, 197, 94, 0.5);
}

.vad-event-strip {
  display: grid;
  gap: 10px;
  padding: 16px 18px;
  border-radius: 20px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background:
    linear-gradient(180deg, rgba(15, 23, 42, 0.52), rgba(30, 41, 59, 0.28)),
    radial-gradient(circle at top right, rgba(34, 197, 94, 0.08), transparent 28%);
}

.vad-strip-title {
  color: #94a3b8;
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.vad-event-list {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.vad-event-chip {
  padding: 8px 12px;
  border-radius: 999px;
  color: #dcfce7;
  font-family: var(--mono-font);
  font-size: 12px;
  background: rgba(34, 197, 94, 0.12);
  border: 1px solid rgba(34, 197, 94, 0.18);
}

.vad-event-empty {
  color: #64748b;
  font-family: var(--mono-font);
}

.upload-panel {
  width: 100%;
}

:deep(.upload-panel .el-upload-dragger) {
  width: 100%;
  border-radius: 24px;
  border-style: dashed;
  border-color: rgba(0, 240, 255, 0.2);
  background:
    radial-gradient(circle at top, rgba(0, 240, 255, 0.12), transparent 34%),
    linear-gradient(180deg, rgba(15, 23, 42, 0.56), rgba(30, 41, 59, 0.38));
}

.upload-icon {
  font-size: 30px;
  color: #00f0ff;
  filter: drop-shadow(0 0 10px rgba(0, 240, 255, 0.28));
}

.param-grid {
  padding-top: 4px;
}

.inline-note {
  min-height: 40px;
  display: flex;
  align-items: center;
  color: #cbd5e1;
  line-height: 1.5;
}

.param-form {
  display: grid;
  gap: 6px 16px;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.transcript-stream {
  min-height: 300px;
  padding: 18px;
  border-radius: 20px;
  background:
    linear-gradient(180deg, rgba(15, 23, 42, 0.58), rgba(30, 41, 59, 0.36)),
    radial-gradient(circle at top right, rgba(0, 240, 255, 0.08), transparent 30%);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.empty-state {
  color: #64748b;
  font-family: var(--mono-font);
}

.final-segment {
  margin: 0 0 12px;
  color: #f8fafc;
  line-height: 1.7;
  font-family: var(--mono-font);
  animation: final-text-in 0.35s ease both;
}

.partial-segment {
  margin: 0;
  color: #67e8f9;
  font-family: var(--mono-font);
  position: relative;
  display: inline-block;
}

.partial-segment::after {
  content: "";
  display: inline-block;
  width: 10px;
  height: 1.1em;
  margin-left: 6px;
  vertical-align: -0.12em;
  background: linear-gradient(180deg, #00f0ff, #3b82f6);
  box-shadow: 0 0 10px rgba(0, 240, 255, 0.3);
  animation: blink-cursor 0.9s steps(1) infinite;
}

.error-log {
  margin-top: 16px;
  padding: 16px;
  border-radius: 18px;
  background: rgba(239, 68, 68, 0.12);
  color: #fecaca;
  border: 1px solid rgba(239, 68, 68, 0.22);
  animation: pulse-danger 1.8s ease-in-out infinite;
}

.error-log strong {
  display: block;
  margin-bottom: 8px;
}

.error-log p {
  margin: 6px 0 0;
}

.raw-preview {
  margin-top: 18px;
}

.metrics-board :deep(.el-descriptions__content) {
  color: #ffffff !important;
}

@keyframes blink-cursor {
  0%,
  49% {
    opacity: 1;
  }
  50%,
  100% {
    opacity: 0;
  }
}

@keyframes final-text-in {
  from {
    opacity: 0.45;
    transform: translateY(6px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes pulse-danger {
  0%,
  100% {
    box-shadow: 0 0 0 rgba(239, 68, 68, 0);
  }
  50% {
    box-shadow: 0 0 20px rgba(239, 68, 68, 0.14);
  }
}

@media (max-width: 1120px) {
  .stream-status-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .param-form {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 768px) {
  .stream-status-grid {
    grid-template-columns: 1fr;
  }

  .param-form {
    grid-template-columns: 1fr;
  }
}
</style>
