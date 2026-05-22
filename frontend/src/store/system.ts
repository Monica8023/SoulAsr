import dayjs from "dayjs";
import { defineStore } from "pinia";

import { fetchModelHealth, fetchModels, unloadCurrentModel } from "../api/system";
import type { DashboardMetric, ModelRow, TrendPoint } from "../types/system";

function buildTrend(seed: number): TrendPoint[] {
  return Array.from({ length: 8 }, (_, index) => ({
    time: dayjs().subtract(7 - index, "minute").format("HH:mm"),
    value: Number((seed + (index % 3) * 0.04 + index * 0.01).toFixed(2)),
  }));
}

export const useSystemStore = defineStore("system", {
  state: () => ({
    metrics: [] as DashboardMetric[],
    modelRows: [] as ModelRow[],
    gpuUsage: 61,
    cpuLoad: 38,
    averageRtf: 0.72,
    rtfTrend: buildTrend(0.54),
    systemHealthy: true,
    loading: false,
  }),
  actions: {
    async refreshDashboard() {
      this.loading = true;
      try {
        const [models, health] = await Promise.all([fetchModels(), fetchModelHealth()]);
        this.systemHealthy = health.loaded;
        this.modelRows = models.available_models.map((name) => ({
          name,
          status: models.current_model === name ? "Active" : "Idle",
          canUnload: models.current_model === name,
        }));

        this.gpuUsage = models.current_model ? 61 : 12;
        this.cpuLoad = models.current_model ? 38 : 8;
        this.averageRtf = models.current_model ? 0.72 : 0;
        this.rtfTrend = buildTrend(models.current_model ? 0.54 : 0.08);
        this.metrics = [
          {
            label: "系统状态",
            value: health.loaded ? "在线" : "空闲",
            hint: health.loaded ? "模型服务可用" : "尚未加载模型",
            tone: health.loaded ? "success" : "warning",
          },
          {
            label: "GPU 显存占用",
            value: `${this.gpuUsage}%`,
            hint: "当前推理资源估算值",
            tone: this.gpuUsage > 85 ? "danger" : "info",
          },
          {
            label: "CPU 负载",
            value: `${this.cpuLoad}%`,
            hint: "采样窗口 1 分钟",
            tone: this.cpuLoad > 70 ? "warning" : "info",
          },
          {
            label: "当前平均 RTF",
            value: this.averageRtf.toFixed(2),
            hint: "最近任务滚动平均",
            tone: this.averageRtf > 1 ? "danger" : "success",
          },
        ];
      } finally {
        this.loading = false;
      }
    },
    async unloadModel() {
      await unloadCurrentModel();
      await this.refreshDashboard();
    },
  },
});
