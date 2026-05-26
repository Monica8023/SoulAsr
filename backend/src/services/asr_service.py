from __future__ import annotations

from logging import Logger
import time

from fastapi import WebSocket, WebSocketDisconnect

from backend.src.schemas.asr import (
    StreamEndRequest,
    StreamErrorEvent,
    StreamMetricsEvent,
    StreamStartRequest,
    StreamVadEvent,
    TranscriptionRequest,
    TranscriptionResponse,
)
from backend.src.schemas.metrics import AsrMetrics
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
                        await self._safe_send_json(
                            websocket,
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
                        await self._safe_send_json(
                            websocket,
                            {
                                "type": "final" if vad_result.is_sentence_final else "partial",
                                "text": partial_text,
                                "is_final": vad_result.is_sentence_final,
                                "model_name": engine.model_name,
                                "speech_active": vad_result.speech_active,
                                "sentence_index": vad_result.sentence_index,
                            }
                        )
                        await self._safe_send_json(
                            websocket,
                            self._build_stream_metrics_event(
                                elapsed_ms=elapsed_ms,
                                total_audio_seconds=total_audio_seconds,
                                first_token_ms=first_token_ms,
                            ).model_dump()
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
            await self._safe_send_json(
                websocket,
                StreamErrorEvent(
                    code="STREAM_ERROR",
                    detail=str(exc),
                ).model_dump()
            )
        finally:
            await self._safe_close(websocket)

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
            await self._safe_send_json(
                websocket,
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
            await self._safe_send_json(
                websocket,
                {
                    "type": "final",
                    "text": final_text,
                    "is_final": True,
                    "model_name": engine.model_name,
                    "speech_active": False,
                    "sentence_index": vad_finalize.sentence_index,
                }
            )
        await self._safe_send_json(
            websocket,
            self._build_stream_metrics_event(
                elapsed_ms=total_duration_ms,
                total_audio_seconds=final_audio_seconds,
                first_token_ms=first_token_ms,
            ).model_dump()
        )
        rtf = (
            round((total_duration_ms / 1000) / final_audio_seconds, 4)
            if final_audio_seconds and final_audio_seconds > 0
            else 0.0
        )
        self.logger.info(
            "Streaming session finalized. model_name=%s total_duration_ms=%s audio_seconds=%s rtf=%s",
            engine.model_name,
            total_duration_ms,
            final_audio_seconds,
            rtf,
        )

    def _build_stream_metrics_event(
        self,
        elapsed_ms: float,
        total_audio_seconds: float | None,
        first_token_ms: float | None,
    ) -> StreamMetricsEvent:
        resolved_first_token_ms = first_token_ms if first_token_ms is not None else elapsed_ms
        rtf = (
            round((elapsed_ms / 1000) / total_audio_seconds, 4)
            if total_audio_seconds and total_audio_seconds > 0
            else 0.0
        )
        return StreamMetricsEvent(
            rtf=rtf,
            latency_ms=elapsed_ms,
            first_token_ms=resolved_first_token_ms,
            total_duration_ms=elapsed_ms,
            audio_seconds=total_audio_seconds,
        )

    async def _safe_send_json(self, websocket: WebSocket, payload: dict):
        try:
            await websocket.send_json(payload)
        except (RuntimeError, WebSocketDisconnect) as exc:
            self.logger.info("Skip websocket send because connection is closing: %s", exc)

    async def _safe_close(self, websocket: WebSocket):
        try:
            await websocket.close()
        except RuntimeError as exc:
            self.logger.info("Skip websocket close because connection is already closed: %s", exc)

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
