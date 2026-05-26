<template>
  <aside class="sidebar">
    <div>
      <div class="brand-block">
        <p class="brand-kicker">SoulASR</p>
        <h2>Test Console</h2>
        <p class="brand-copy">
          本地语音识别性能与效果测试平台，聚焦资源监控、实时调试与流式识别链路验证。
        </p>
      </div>

      <el-menu
        :default-active="activePath"
        class="sidebar-menu"
        :router="true"
        background-color="transparent"
        text-color="#d8e4ec"
        active-text-color="#ffffff"
      >
        <el-menu-item
          v-for="item in items"
          :key="item.path"
          :index="item.path"
          class="sidebar-item"
        >
          <el-icon><component :is="item.icon" /></el-icon>
          <span>{{ item.label }}</span>
        </el-menu-item>
      </el-menu>
    </div>

    <div class="status-card">
      <span class="status-dot" />
      <div>
        <strong>Workspace Ready</strong>
        <p>前端已按 TS 架构拆分，等待真实 WebSocket 和监控接口接入。</p>
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { DataLine, Microphone } from "@element-plus/icons-vue";
import { computed } from "vue";
import { useRoute } from "vue-router";

const route = useRoute();

const activePath = computed(() => route.path);

const items = [
  { path: "/", label: "系统仪表盘", icon: DataLine },
  { path: "/workbench", label: "ASR 调试工作台", icon: Microphone },
];
</script>

<style scoped>
.sidebar {
  width: 292px;
  padding: 28px 18px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  color: #f8fbff;
  background:
    radial-gradient(circle at top left, rgba(0, 240, 255, 0.16), transparent 26%),
    radial-gradient(circle at bottom right, rgba(124, 58, 237, 0.18), transparent 24%),
    linear-gradient(180deg, rgba(7, 11, 19, 0.96) 0%, rgba(11, 18, 32, 0.94) 100%);
  border-right: 1px solid rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(16px);
  position: relative;
}

.sidebar::after {
  content: "";
  position: absolute;
  inset: 0 0 auto;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(0, 240, 255, 0.7), transparent);
}

.brand-block {
  padding: 10px 12px 22px;
}

.brand-kicker {
  margin: 0 0 8px;
  font-size: 12px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: rgba(125, 211, 252, 0.84);
}

.brand-block h2 {
  margin: 0;
  font-size: 32px;
  line-height: 1.05;
  text-shadow: 0 0 20px rgba(0, 240, 255, 0.14);
}

.brand-copy {
  margin: 14px 0 0;
  line-height: 1.75;
  color: rgba(248, 251, 255, 0.78);
}

.sidebar-menu {
  border-right: 0;
}

:deep(.sidebar-menu .el-menu-item) {
  height: 52px;
  margin-bottom: 8px;
  border-radius: 16px;
  background: rgba(15, 23, 42, 0.34);
  border: 1px solid transparent;
}

:deep(.sidebar-menu .el-menu-item.is-active) {
  background: linear-gradient(90deg, rgba(0, 240, 255, 0.14), rgba(124, 58, 237, 0.12));
  border: 1px solid rgba(0, 240, 255, 0.22);
  box-shadow: inset 0 0 18px rgba(0, 240, 255, 0.08), 0 0 18px rgba(0, 240, 255, 0.08);
}

.status-card {
  display: grid;
  grid-template-columns: 10px 1fr;
  gap: 12px;
  padding: 16px;
  margin: 12px;
  border-radius: 20px;
  background: rgba(30, 41, 59, 0.58);
  border: 1px solid rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(14px);
}

.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  margin-top: 6px;
  background: #10b981;
  box-shadow:
    0 0 0 6px rgba(16, 185, 129, 0.1),
    0 0 18px rgba(16, 185, 129, 0.34);
  animation: status-breathe 1.8s ease-in-out infinite;
}

.status-card strong {
  display: block;
  margin-bottom: 6px;
}

.status-card p {
  margin: 0;
  font-size: 13px;
  line-height: 1.6;
  color: rgba(248, 251, 255, 0.7);
}

@keyframes status-breathe {
  0%,
  100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.12);
  }
}

@media (max-width: 960px) {
  .sidebar {
    display: none;
  }
}
</style>
