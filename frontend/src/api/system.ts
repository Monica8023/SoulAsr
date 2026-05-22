import type { AxiosResponse } from "axios";

import client from "./client";
import type { ModelHealth, ModelListResponse } from "../types/system";

export function fetchModels() {
  return client
    .get<never, AxiosResponse<ModelListResponse>>("/models")
    .then((response) => response.data);
}

export function fetchModelHealth() {
  return client
    .get<never, AxiosResponse<ModelHealth>>("/models/health")
    .then((response) => response.data);
}

export function unloadCurrentModel() {
  return client
    .post<never, AxiosResponse<{ current_model: string | null }>>("/models/unload")
    .then((response) => response.data);
}
