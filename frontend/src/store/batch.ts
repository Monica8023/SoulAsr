import dayjs from "dayjs";
import { defineStore } from "pinia";

import type { BatchTask } from "../types/batch";

function makeTask(index: number): BatchTask {
  const progress = [25, 60, 100, 87][index % 4];
  const status = progress === 100 ? "finished" : progress > 50 ? "running" : "queued";
  return {
    id: `task-${index + 1}`,
    fileName: `sample_${index + 1}.wav`,
    modelName: index % 2 === 0 ? "whisper" : "funasr",
    status,
    progress,
    rtf: Number((0.54 + index * 0.08).toFixed(2)),
    duration: `${18 + index * 4}s`,
    startedAt: dayjs().subtract(index * 6, "minute").format("YYYY-MM-DD HH:mm:ss"),
  };
}

export const useBatchStore = defineStore("batch", {
  state: () => ({
    tasks: Array.from({ length: 6 }, (_, index) => makeTask(index)),
  }),
  actions: {
    reseedTasks() {
      this.tasks = Array.from({ length: 6 }, (_, index) => makeTask(index + 1));
    },
    updateTask(id: string, patch: Partial<BatchTask>) {
      const target = this.tasks.find((task) => task.id === id);
      if (target) {
        Object.assign(target, patch);
      }
    },
  },
});
