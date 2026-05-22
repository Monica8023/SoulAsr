import { saveAs } from "file-saver";

import type { BatchTask } from "../types/batch";

export function exportBatchTasks(tasks: BatchTask[]) {
  const header = ["fileName", "modelName", "status", "progress", "rtf", "duration"];
  const rows = tasks.map((task) =>
    [task.fileName, task.modelName, task.status, task.progress, task.rtf, task.duration].join(","),
  );

  const csv = [header.join(","), ...rows].join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  saveAs(blob, "batch-test-report.csv");
}
