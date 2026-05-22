from __future__ import annotations

import struct
from typing import Any

import numpy as np
from funasr import AutoModel

from backend.src.core.logging_config import get_logger
from backend.src.services.vad_service import BaseVadProvider

logger = get_logger(__name__)

_vad_model = None
_VAD_SAMPLE_RATE = 16000
_SHORT_CHUNK_WINDOW_MS = 60
_SHORT_CHUNK_WINDOW_SAMPLES = _VAD_SAMPLE_RATE * _SHORT_CHUNK_WINDOW_MS // 1000


def load_vad_model(model_path: str, device: str):
    global _vad_model

    if _vad_model is not None:
        return _vad_model

    logger.info("Loading streaming VAD model from %s on device=%s", model_path, device)
    _vad_model = AutoModel(
        model=model_path,
        device=device,
        disable_update=True,
    )
    logger.info("Streaming VAD model loaded.")
    return _vad_model


class VADDetector:
    def __init__(
        self,
        threshold_ms: int = 2000,
        silence_tolerance_ms: int = 200,
        energy_threshold: int = 1500,
    ):
        self.threshold_ms = int(threshold_ms)
        self.silence_tolerance_ms = max(0, int(silence_tolerance_ms))
        self._energy_threshold = energy_threshold

        self._speech_active = False
        self._speech_elapsed_ms = 0
        self._speech_gap_ms = 0
        self._last_progress_log_ms = 0
        self._interrupted = False

        self._vad_cache: dict[str, Any] = {}
        self._is_speaking = False
        self._cache_frame_count = 0
        self._cache_reset_interval_frames = 6000
        self._short_chunk_history = bytearray()

    def reset(self) -> None:
        self.reset_interrupt_state()
        self.reset_detection_state()

    def reset_interrupt_state(self) -> None:
        self._speech_active = False
        self._speech_elapsed_ms = 0
        self._speech_gap_ms = 0
        self._last_progress_log_ms = 0
        self._interrupted = False

    def reset_detection_state(self) -> None:
        self._vad_cache = {}
        self._is_speaking = False
        self._cache_frame_count = 0
        self._short_chunk_history.clear()

    @staticmethod
    def _extract_events(result) -> list:
        if isinstance(result, list) and result:
            first = result[0]
            if isinstance(first, dict):
                return first.get("value") or []
        return []

    def _run_streaming_vad(self, audio_bytes: bytes) -> bool:
        if _vad_model is None:
            raise RuntimeError("streaming VAD model is not loaded")

        audio_np = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        chunk_ms = max(1, len(audio_np) // 16)
        result = _vad_model.generate(
            input=audio_np,
            cache=self._vad_cache,
            is_final=False,
            chunk_size=chunk_ms,
            disable_pbar=True,
        )
        self._cache_frame_count += 1
        if self._cache_frame_count >= self._cache_reset_interval_frames:
            self._vad_cache = {}
            self._cache_frame_count = 0

        events = self._extract_events(result)
        if events:
            for event in events:
                start, end = event[0], event[1]
                if start != -1 and end == -1:
                    self._is_speaking = True
                elif start == -1 and end != -1:
                    self._is_speaking = False
        return self._is_speaking

    def _run_short_chunk_vad(self, audio_bytes: bytes) -> bool:
        if _vad_model is None:
            raise RuntimeError("streaming VAD model is not loaded")

        self._short_chunk_history.extend(audio_bytes)
        max_history_bytes = _SHORT_CHUNK_WINDOW_SAMPLES * 2
        if len(self._short_chunk_history) > max_history_bytes:
            del self._short_chunk_history[:-max_history_bytes]

        buffered_samples = len(self._short_chunk_history) // 2
        if buffered_samples < _SHORT_CHUNK_WINDOW_SAMPLES:
            logger.debug(
                "VAD buffering short chunk: buffered_samples=%d min_required=%d",
                buffered_samples,
                _SHORT_CHUNK_WINDOW_SAMPLES,
            )
            return self._is_speaking

        window_audio = bytes(self._short_chunk_history)
        audio_np = np.frombuffer(window_audio, dtype=np.int16).astype(np.float32) / 32768.0
        chunk_ms = max(1, len(audio_np) // 16)
        result = _vad_model.generate(
            input=audio_np,
            cache={},
            is_final=False,
            chunk_size=chunk_ms,
            disable_pbar=True,
        )
        events = self._extract_events(result)
        if events:
            for event in events:
                start, end = event[0], event[1]
                if start != -1 and end == -1:
                    self._is_speaking = True
                elif start == -1 and end != -1:
                    self._is_speaking = False
        return self._is_speaking

    def is_speech(self, audio_bytes: bytes) -> bool:
        if len(audio_bytes) < 2:
            return self._is_speaking

        if _vad_model is not None:
            if len(audio_bytes) % 2 != 0:
                audio_bytes = audio_bytes[:-1]
                if not audio_bytes:
                    return self._is_speaking

            num_samples = len(audio_bytes) // 2
            try:
                if num_samples < _SHORT_CHUNK_WINDOW_SAMPLES:
                    return self._run_short_chunk_vad(audio_bytes)
                return self._run_streaming_vad(audio_bytes)
            except Exception as exc:
                self._vad_cache = {}
                self._cache_frame_count = 0
                if num_samples < _SHORT_CHUNK_WINDOW_SAMPLES:
                    logger.warning("Streaming VAD short-chunk inference failed, fallback to energy: %s", exc)
                else:
                    logger.warning("Streaming VAD inference failed, fallback to energy: %s", exc)

        samples = struct.unpack_from(f"{len(audio_bytes) // 2}h", audio_bytes)
        rms = (sum(sample * sample for sample in samples) / len(samples)) ** 0.5
        self._is_speaking = rms > self._energy_threshold
        return self._is_speaking

    def process_speech(self, speech: bool, chunk_ms: int = 0, allow_trigger: bool = True) -> bool:
        if speech:
            if not self._speech_active:
                self._speech_active = True
                self._speech_elapsed_ms = 0
                self._speech_gap_ms = 0
                self._last_progress_log_ms = 0
                self._interrupted = False
                logger.debug("VAD: speech started")

            self._speech_gap_ms = 0
            self._speech_elapsed_ms += max(0, int(chunk_ms or 0))
            if (
                allow_trigger
                and not self._interrupted
                and self._speech_elapsed_ms - self._last_progress_log_ms >= 500
            ):
                self._last_progress_log_ms = self._speech_elapsed_ms
                logger.info(
                    "VAD: continuous speech progress %d/%d ms",
                    self._speech_elapsed_ms,
                    self.threshold_ms,
                )
            if allow_trigger and self._speech_elapsed_ms >= self.threshold_ms and not self._interrupted:
                self._interrupted = True
                logger.info(
                    "VAD: continuous speech %d ms >= threshold %d ms, triggering interrupt",
                    self._speech_elapsed_ms,
                    self.threshold_ms,
                )
                return True
        else:
            gap_ms = max(0, int(chunk_ms or 0))
            if self._speech_active and gap_ms and self._speech_gap_ms + gap_ms <= self.silence_tolerance_ms:
                self._speech_gap_ms += gap_ms
                logger.debug(
                    "VAD: speech gap tolerated %d/%d ms",
                    self._speech_gap_ms,
                    self.silence_tolerance_ms,
                )
                return False
            if self._speech_active:
                logger.debug("VAD: speech ended after %d ms", self._speech_elapsed_ms)
            self._speech_active = False
            self._speech_elapsed_ms = 0
            self._speech_gap_ms = 0
            self._last_progress_log_ms = 0
            self._interrupted = False

        return False

    def process(self, audio_bytes: bytes) -> bool:
        chunk_ms = int((len(audio_bytes) // 2) / _VAD_SAMPLE_RATE * 1000)
        return self.process_speech(self.is_speech(audio_bytes), chunk_ms)


class StreamingVadProvider(BaseVadProvider):
    def __init__(self, model_path: str, device: str = "cpu", energy_threshold: int = 1500):
        self.model_path = model_path
        self.device = device
        self.energy_threshold = energy_threshold
        load_vad_model(model_path=model_path, device=device)

    def create_session(self) -> VADDetector:
        return VADDetector(energy_threshold=self.energy_threshold)

    def process_chunk(
        self,
        session: VADDetector,
        audio_bytes: bytes,
        sample_rate: int,
        channels: int,
    ) -> dict[str, Any]:
        speech_active = session.is_speech(audio_bytes)
        return {
            "speech_active": speech_active,
        }

    def finalize_session(self, session: VADDetector) -> dict[str, Any]:
        speech_active = session._is_speaking
        session.reset()
        return {
            "speech_active": False,
            "should_transcribe": speech_active,
            "is_sentence_final": speech_active,
        }
