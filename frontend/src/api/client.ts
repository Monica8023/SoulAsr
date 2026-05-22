import axios, { AxiosError, type AxiosResponse } from "axios";
import { ElMessage } from "element-plus";

import type { ApiResponse } from "../types/api";

const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1",
  timeout: 15000,
});

client.interceptors.response.use(
  (response): AxiosResponse => {
    const payload = response.data as ApiResponse<unknown> | unknown;

    if (
      payload &&
      typeof payload === "object" &&
      "code" in payload &&
      "message" in payload
    ) {
      const envelope = payload as ApiResponse<unknown>;
      if (envelope.code !== 0) {
        ElMessage.error(envelope.message || "请求失败");
        throw new Error(envelope.message || "请求失败");
      }
      response.data = envelope.data;
      return response;
    }

    return response;
  },
  (error: AxiosError<{ detail?: string; message?: string }>) => {
    const message =
      error.response?.data?.detail ||
      error.response?.data?.message ||
      error.message ||
      "网络请求失败";
    ElMessage.error(message);
    return Promise.reject(error);
  },
);

export default client;
