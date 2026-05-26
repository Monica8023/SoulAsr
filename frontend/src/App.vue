<template>
  <el-container class="app-shell">
    <AppSidebar />
    <el-container>
      <el-header class="app-header">
        <div class="header-copy">
          <p class="app-kicker">Local ASR QA Console</p>
          <h1>{{ pageTitle }}</h1>
          <p class="header-subtitle">Cyber-Tech Interface for streaming recognition, model control, and realtime diagnostics.</p>
        </div>
        <el-tag effect="dark" round class="runtime-tag">Vue 3 + TypeScript</el-tag>
      </el-header>
      <el-main class="app-main">
        <RouterView />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useRoute } from "vue-router";

import AppSidebar from "./components/layout/AppSidebar.vue";

const route = useRoute();

const pageTitle = computed(() => (route.meta.title as string) || "ASR Test Platform");
</script>

<style scoped>
.app-shell {
  min-height: 100vh;
  background: transparent;
}

.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 28px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(11, 14, 20, 0.46);
  backdrop-filter: blur(18px);
}

.app-header h1 {
  margin: 0;
  font-size: 30px;
  color: #fff;
  text-shadow: 0 0 16px rgba(0, 240, 255, 0.16);
}

.app-kicker {
  margin: 0 0 4px;
  font-size: 12px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: #7dd3fc;
}

.header-copy {
  display: grid;
  gap: 2px;
}

.header-subtitle {
  margin: 4px 0 0;
  color: #94a3b8;
}

.runtime-tag {
  background: rgba(59, 130, 246, 0.14) !important;
  border-color: rgba(0, 240, 255, 0.18) !important;
  color: #8be9ff !important;
  box-shadow: 0 0 16px rgba(0, 240, 255, 0.1);
}

.app-main {
  padding: 28px;
}

@media (max-width: 960px) {
  .app-header {
    padding: 18px 20px;
  }

  .app-main {
    padding: 20px;
  }
}
</style>
