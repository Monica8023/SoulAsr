export interface BatchTask {
  id: string;
  fileName: string;
  modelName: string;
  status: "queued" | "running" | "finished" | "error";
  progress: number;
  rtf: number;
  duration: string;
  startedAt: string;
}
