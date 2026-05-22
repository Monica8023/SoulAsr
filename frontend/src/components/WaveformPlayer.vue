<template>
  <div class="waveform-shell">
    <div ref="waveformRef" class="waveform-view" />
    <div class="waveform-toolbar">
      <div class="toolbar-left">
        <el-button size="small" @click="togglePlayback" :disabled="!ready">
          {{ playing ? "暂停" : "播放" }}
        </el-button>
        <span class="muted">{{ durationLabel }}</span>
      </div>
      <div class="toolbar-right">
        <span class="muted">缩放</span>
        <el-slider v-model="zoomValue" :min="10" :max="220" :step="10" :disabled="!ready" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import RegionsPlugin from "wavesurfer.js/dist/plugins/regions.esm.js";
import WaveSurfer from "wavesurfer.js";
import { computed, onBeforeUnmount, ref, watch } from "vue";

interface VadSegment {
  start: number;
  end: number;
  color?: string;
}

const props = defineProps<{
  file: File | null;
  vadSegments?: VadSegment[];
}>();

const emit = defineEmits<{
  ready: [duration: number];
}>();

const waveformRef = ref<HTMLDivElement | null>(null);
const ready = ref(false);
const playing = ref(false);
const duration = ref(0);
const zoomValue = ref(50);

let waveSurfer: WaveSurfer | null = null;
const regionsPlugin = RegionsPlugin.create();

const durationLabel = computed(() => {
  if (!duration.value) {
    return "尚未加载音频";
  }
  return `时长 ${duration.value.toFixed(2)}s`;
});

const applyRegions = () => {
  if (!waveSurfer) {
    return;
  }
  regionsPlugin.clearRegions();
  props.vadSegments?.forEach((segment) => {
    regionsPlugin.addRegion({
      start: segment.start,
      end: segment.end,
      color: segment.color || "rgba(124, 58, 237, 0.3)",
      drag: false,
      resize: false,
    });
  });
};

const createWaveSurfer = () => {
  if (!waveformRef.value) {
    return;
  }

  waveSurfer?.destroy();
  waveSurfer = WaveSurfer.create({
    container: waveformRef.value,
    waveColor: "rgba(148, 163, 184, 0.3)",
    progressColor: "#00f0ff",
    cursorColor: "#00f0ff",
    height: 140,
    barWidth: 2,
    barGap: 1,
    cursorWidth: 2,
    normalize: true,
    plugins: [regionsPlugin],
  });

  waveSurfer.on("ready", () => {
    ready.value = true;
    duration.value = waveSurfer?.getDuration() || 0;
    emit("ready", duration.value);
    applyRegions();
  });

  waveSurfer.on("play", () => {
    playing.value = true;
  });

  waveSurfer.on("pause", () => {
    playing.value = false;
  });
};

const togglePlayback = () => {
  waveSurfer?.playPause();
};

watch(zoomValue, (value) => {
  waveSurfer?.zoom(value);
});

watch(
  () => props.file,
  async (file) => {
    ready.value = false;
    playing.value = false;
    duration.value = 0;

    if (!file) {
      return;
    }

    if (!waveSurfer) {
      createWaveSurfer();
    }

    await waveSurfer?.loadBlob(file);
  },
  { immediate: true },
);

watch(
  () => props.vadSegments,
  () => {
    applyRegions();
  },
  { deep: true },
);

onBeforeUnmount(() => {
  waveSurfer?.destroy();
});
</script>

<style scoped>
.waveform-shell {
  display: grid;
  gap: 14px;
}

.waveform-view {
  min-height: 150px;
  padding: 12px 0;
  border-radius: 18px;
  background:
    linear-gradient(180deg, rgba(15, 23, 42, 0.5), rgba(30, 41, 59, 0.32)),
    radial-gradient(circle at center, rgba(0, 240, 255, 0.08), transparent 56%);
  border: 1px solid rgba(255, 255, 255, 0.08);
  box-shadow: inset 0 0 26px rgba(0, 240, 255, 0.04);
}

.waveform-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.toolbar-left,
.toolbar-right {
  display: flex;
  align-items: center;
  gap: 14px;
}

.toolbar-right {
  min-width: min(360px, 100%);
}

:deep(wave) {
  filter: drop-shadow(0 0 8px rgba(0, 240, 255, 0.16));
}

@media (max-width: 768px) {
  .waveform-toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .toolbar-right {
    min-width: 100%;
  }
}
</style>
