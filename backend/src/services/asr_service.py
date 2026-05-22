from __future__ import annotations

import asyncio
from logging import Logger
from pathlib import Path
import time
from uuid import uuid4

from fastapi import BackgroundTasks, HTTPException, UploadFile, WebSocket, WebSocketDisconnect

from backend.src.schemas.asr import (
    BatchTranscriptionRequest,
    BatchTranscriptionResponse,
    StreamEndRequest,
    StreamErrorEvent,
    StreamMetricsEvent,
    StreamStartRequest,
    StreamVadEvent,
    TranscriptionRequest,
    TranscriptionResponse,
)
from backend.src.schemas.batch import (
    BatchResultItem,
    BatchTaskCreateResponse,
    BatchTaskRecord,
    BatchTaskResultResponse,
    BatchTaskStatusResponse,
)
from backend.src.schemas.metrics import AsrMetrics
from backend.src.core.config import settings
from backend.src.core.logging_config import get_logger
from backend.src.services.audio_processor import AudioProcessor
from backend.src.services.vad_provider import build_vad_provider
from backend.src.services.vad_service import VadService


class AsrService:
    def __init__(self, model_manager):
        self.logger: Logger = get_logger(__name__)
        self.model_manager = model_manager
        self.audio_processor = AudioProcessor()
        self.vad_service = VadService(
            audio_processor=self.audio_processor,
            provider=build_vad_provider(),
        )
        self._batch_tasks: dict[str, BatchTaskRecord] = {}

    def transcribe(self, payload: TranscriptionRequest) -> TranscriptionResponse:
        self.logger.info("Offline transcription requested. model_name=%s audio_path=%s", payload.model_name, payload.audio_path)
        prepared_audio = self.audio_processor.prepare_audio_path(payload.audio_path)
        try:
            return self._transcribe_prepared_audio(
                prepared_audio=prepared_audio,
                model_name=payload.model_name,
                options=payload.options,
                response_audio_path=payload.audio_path,
            )
        finally:
            self.audio_processor.cleanup_prepared_audio(prepared_audio)

    def transcribe_batch(self, payload: BatchTranscriptionRequest) -> BatchTranscriptionResponse:
        items = [
            self.transcribe(
                TranscriptionRequest(
                    audio_path=audio_path,
                    model_name=payload.model_name,
                    options=payload.options,
                )
            )
            for audio_path in payload.audio_paths
        ]
        return BatchTranscriptionResponse(items=items, total=len(items))

    async def create_batch_task(
        self,
        files: list[UploadFile],
        model_name: str | None,
        options,
        background_tasks: BackgroundTasks,
    ) -> BatchTaskCreateResponse:
        task_id = uuid4().hex
        prepared_files = [await self.audio_processor.persist_upload(file) for file in files]
        self.logger.info(
            "Batch task created. task_id=%s total_files=%s model_name=%s",
            task_id,
            len(prepared_files),
            model_name,
        )
        self._batch_tasks[task_id] = BatchTaskRecord(
            task_id=task_id,
            status="queued",
            progress=0.0,
            total_files=len(prepared_files),
            completed_files=0,
        )
        background_tasks.add_task(
            self._process_batch_task,
            task_id,
            prepared_files,
            model_name,
            options,
        )
        return BatchTaskCreateResponse(task_id=task_id, status="queued", progress=0.0)

    def get_batch_task_status(self, task_id: str) -> BatchTaskStatusResponse:
        task = self._require_task(task_id)
        return BatchTaskStatusResponse(
            task_id=task.task_id,
            status=task.status,
            progress=task.progress,
            total_files=task.total_files,
            completed_files=task.completed_files,
            error=task.error,
        )

    def get_batch_task_result(self, task_id: str) -> BatchTaskResultResponse:
        task = self._require_task(task_id)
        items = [
            BatchResultItem(
                file_name=Path(item.audio_path).name,
                text=item.text,
                model_name=item.model_name,
                total_duration_ms=item.metrics.latency_ms,
                rtf=item.metrics.rtf,
            )
            for item in task.items
        ]
        return BatchTaskResultResponse(task_id=task.task_id, status=task.status, items=items)

    async def handle_streaming_session(self, websocket: WebSocket):
        await websocket.accept()
        self.logger.info("WebSocket streaming session accepted.")
        stream_config: StreamStartRequest | None = None
        engine = None
        stream_session = None
        vad_session = None
        stream_started_at = None
        first_token_ms: float | None = None
        total_audio_seconds = 0.0

        try:
            while True:
                message = await websocket.receive()
                message_type = message.get("type")

                if message_type == "websocket.disconnect":
                    break

                if message.get("text"):
                    text = message["text"]
                    if stream_config is None:
                        stream_config = StreamStartRequest.model_validate_json(text)
                        self.logger.info(
                            "Streaming session started. model_name=%s file_name=%s audio_format=%s sample_rate=%s channels=%s",
                            stream_config.model_name,
                            stream_config.file_name,
                            stream_config.audio_format,
                            stream_config.sample_rate,
                            stream_config.channels,
                        )
                        engine = self.model_manager.get_engine(stream_config.model_name)
                        stream_session = engine.create_stream_session(
                            file_name=stream_config.file_name,
                            language=stream_config.options.language,
                            hotwords=stream_config.options.hotwords,
                            enable_itn=stream_config.options.enable_itn,
                            sample_rate=stream_config.sample_rate,
                            channels=stream_config.channels,
                            audio_format=stream_config.audio_format,
                        )
                        vad_session = self.vad_service.create_session()
                        stream_started_at = time.perf_counter()
                        continue

                    end_message = StreamEndRequest.model_validate_json(text)
                    if end_message.type == "end":
                        break

                if message.get("bytes"):
                    if stream_config is None or engine is None or stream_session is None or vad_session is None:
                        raise ValueError("missing stream start message")

                    vad_result = self.vad_service.process_realtime_chunk(
                        session=vad_session,
                        audio_bytes=message["bytes"],
                        sample_rate=stream_config.sample_rate,
                        channels=stream_config.channels,
                        audio_format=stream_config.audio_format,
                    )
                    total_audio_seconds += vad_result.duration_seconds
                    if vad_result.state_changed or vad_result.is_sentence_final:
                        await websocket.send_json(
                            StreamVadEvent(
                                speech_active=vad_result.speech_active,
                                is_sentence_final=vad_result.is_sentence_final,
                                sentence_index=vad_result.sentence_index,
                                should_transcribe=vad_result.should_transcribe,
                            ).model_dump()
                        )
                    if not vad_result.should_transcribe:
                        continue

                    partial_text = engine.transcribe_stream_chunk(
                        session=stream_session,
                        audio_chunk=vad_result.audio_bytes,
                        is_final=vad_result.is_sentence_final,
                    )
                    if partial_text:
                        elapsed_ms = round((time.perf_counter() - stream_started_at) * 1000, 2)
                        if first_token_ms is None:
                            first_token_ms = elapsed_ms
                        await websocket.send_json(
                            {
                                "type": "final" if vad_result.is_sentence_final else "partial",
                                "text": partial_text,
                                "is_final": vad_result.is_sentence_final,
                                "model_name": engine.model_name,
                                "speech_active": vad_result.speech_active,
                                "sentence_index": vad_result.sentence_index,
                            }
                        )

            if stream_config is None:
                raise ValueError("missing stream start message")
            if engine is None or stream_session is None or stream_started_at is None or vad_session is None:
                raise ValueError("stream session was not initialized")

            await self._finalize_streaming_inference(
                websocket=websocket,
                stream_config=stream_config,
                engine=engine,
                stream_session=stream_session,
                vad_session=vad_session,
                stream_started_at=stream_started_at,
                total_audio_seconds=total_audio_seconds,
                first_token_ms=first_token_ms,
            )
        except WebSocketDisconnect:
            self.logger.info("WebSocket streaming session disconnected by client.")
            return
        except Exception as exc:
            self.logger.exception("Streaming session failed: %s", exc)
            await websocket.send_json(
                StreamErrorEvent(
                    code="STREAM_ERROR",
                    detail=str(exc),
                ).model_dump()
            )
        finally:
            await websocket.close()

    def _process_batch_task(
        self,
        task_id: str,
        prepared_files: list,
        model_name: str | None,
        options,
    ):
        task = self._require_task(task_id)
        task.status = "running"
        self.logger.info("Batch task running. task_id=%s", task_id)

        try:
            for index, prepared_audio in enumerate(prepared_files, start=1):
                item = self._transcribe_prepared_audio(
                    prepared_audio=prepared_audio,
                    model_name=model_name,
                    options=options,
                    response_audio_path=prepared_audio.file_name,
                )
                task.items.append(item)
                task.completed_files = index
                task.progress = round((index / task.total_files) * 100, 2)

            task.status = "completed"
            self.logger.info("Batch task completed. task_id=%s total_files=%s", task_id, task.total_files)
        except Exception as exc:
            task.status = "failed"
            task.error = str(exc)
            self.logger.exception("Batch task failed. task_id=%s error=%s", task_id, exc)
        finally:
            for prepared_audio in prepared_files:
                self.audio_processor.cleanup_prepared_audio(prepared_audio)

    async def _finalize_streaming_inference(
        self,
        websocket: WebSocket,
        stream_config: StreamStartRequest,
        engine,
        stream_session,
        vad_session,
        stream_started_at: float,
        total_audio_seconds: float,
        first_token_ms: float | None,
    ):
        vad_finalize = self.vad_service.finalize_session(vad_session)
        if vad_finalize.state_changed or vad_finalize.is_sentence_final:
            await websocket.send_json(
                StreamVadEvent(
                    speech_active=vad_finalize.speech_active,
                    is_sentence_final=vad_finalize.is_sentence_final,
                    sentence_index=vad_finalize.sentence_index,
                    should_transcribe=vad_finalize.should_transcribe,
                ).model_dump()
            )
        final_text = engine.transcribe_stream_chunk(
            stream_session,
            audio_chunk=vad_finalize.audio_bytes,
            is_final=True,
        )
        total_duration_ms = round((time.perf_counter() - stream_started_at) * 1000, 2)
        final_audio_seconds = total_audio_seconds or None
        if first_token_ms is None:
            first_token_ms = total_duration_ms

        if final_text:
            await websocket.send_json(
                {
                    "type": "final",
                    "text": final_text,
                    "is_final": True,
                    "model_name": engine.model_name,
                    "speech_active": False,
                    "sentence_index": vad_finalize.sentence_index,
                }
            )
        rtf = (
            round((total_duration_ms / 1000) / final_audio_seconds, 4)
            if final_audio_seconds and final_audio_seconds > 0
            else 0.0
        )
        await websocket.send_json(
            StreamMetricsEvent(
                rtf=rtf,
                latency_ms=total_duration_ms,
                first_token_ms=first_token_ms,
                total_duration_ms=total_duration_ms,
                audio_seconds=final_audio_seconds,
            ).model_dump()
        )
        self.logger.info(
            "Streaming session finalized. model_name=%s total_duration_ms=%s audio_seconds=%s rtf=%s",
            engine.model_name,
            total_duration_ms,
            final_audio_seconds,
            rtf,
        )

    async def _maybe_delay_stream(
        self,
        stream_config: StreamStartRequest,
        duration: float | None,
        chunk_count: int,
    ):
        if chunk_count <= 0:
            return

        if stream_config.options.push_by_realtime and duration and duration > 0:
            await asyncio.sleep(duration / chunk_count)
            return

        await asyncio.sleep(0.001 * settings.simulated_stream_min_delay_ms)

    def _split_text_for_stream(self, text: str) -> list[str]:
        chunk_count = max(1, min(settings.simulated_stream_chunk_count, len(text.split()) or 1))
        tokens = text.split()
        if len(tokens) <= 1:
            return [text]

        chunk_size = max(1, len(tokens) // chunk_count)
        segments = [
            " ".join(tokens[index : index + chunk_size])
            for index in range(0, len(tokens), chunk_size)
        ]
        return segments or [text]

    def _require_task(self, task_id: str) -> BatchTaskRecord:
        task = self._batch_tasks.get(task_id)
        if task is None:
            raise HTTPException(status_code=404, detail=f"task not found: {task_id}")
        return task

    def _transcribe_prepared_audio(
        self,
        prepared_audio,
        model_name: str | None,
        options,
        response_audio_path: str,
    ) -> TranscriptionResponse:
        engine = self.model_manager.get_engine(model_name)

        start = time.perf_counter()
        text = engine.transcribe(
            prepared_audio.normalized_path,
            language=options.language,
            hotwords=options.hotwords,
            enable_itn=options.enable_itn,
        )
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        duration = prepared_audio.audio_seconds
        rtf = round((latency_ms / 1000) / duration, 4) if duration and duration > 0 else 0.0

        metrics = AsrMetrics(
            latency_ms=latency_ms,
            rtf=rtf,
            audio_seconds=duration,
        )
        return TranscriptionResponse(
            model_name=engine.model_name,
            audio_path=response_audio_path,
            text=text,
            metrics=metrics,
        )
