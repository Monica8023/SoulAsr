import type { AxiosResponse } from "axios";

import client from "./client";
import type {
  BatchTranscriptionRequest,
  BatchTranscriptionResponse,
} from "../types/asr";

export function runBatchTranscription(payload: BatchTranscriptionRequest) {
  return client
    .post<BatchTranscriptionRequest, AxiosResponse<BatchTranscriptionResponse>>(
      "/asr/batch",
      payload,
    )
    .then((response) => response.data);
}
