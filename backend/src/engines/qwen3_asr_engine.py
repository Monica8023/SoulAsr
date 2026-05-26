from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Any

import librosa
import numpy as np
import torch

from backend.src.engines.base_engine import BaseEngine

logger = logging.getLogger(__name__)
_PUNCT_RE = re.compile(r"[\W_]+", re.UNICODE)
_LANGUAGE_MAP = {
    "zh": "Chinese",
    "zh-cn": "Chinese",
    "zh_cn": "Chinese",
    "cn": "Chinese",
    "en": "English",
    "en-us": "English",
    "en_us": "English",
    "english": "English",
    "chinese": "Chinese",
    "auto": None,
}


def _extract_text(payload: Any) -> str:
    if payload is None:
        return ""

    text_attr = getattr(payload, "text", None)
    if isinstance(text_attr, str):
        return text_attr.strip()

    if isinstance(payload, str):
        return payload.strip()

    if isinstance(payload, dict):
        for key in ("text", "transcript", "result", "content"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return ""

    if isinstance(payload, (list, tuple)):
        parts: list[str] = []
        for item in payload:
            text = _extract_text(item)
            if text:
                parts.append(text)
        return "".join(parts).strip()

    return str(payload).strip()


def _delta_text(previous: str, current: str) -> str:
    if not current:
        return ""
    if not previous:
        return current
    if current.startswith(previous):
        return current[len(previous):]
    return current


def _normalize_text(text: str) -> str:
    if not text:
        return ""
    return _PUNCT_RE.sub("", text)


def _resolve_qwen_language(language: str | None) -> str | None:
    if language is None:
        return None
    normalized = str(language).strip()
    if not normalized:
        return None
    mapped = _LANGUAGE_MAP.get(normalized.lower())
    if mapped is not None or normalized.lower() in _LANGUAGE_MAP:
        return mapped
    return normalized[:1].upper() + normalized[1:].lower()


class Qwen3AsrEngine(BaseEngine):
    engine_name = "qwen3-asr"
    _sample_rate = 16000

    def _load_model(self):
        try:
            from qwen_asr import Qwen3ASRModel
        except Exception as exc:
            raise RuntimeError(
                "Failed to import qwen_asr runtime. "
                f"root_cause={type(exc).__name__}: {exc}"
            ) from exc

        cfg = self.runtime_options
        model_path = str(self.model_path)
        dtype_name = str(cfg.get("dtype", "bfloat16")).lower()
        device_map = str(self.device)
        max_inference_batch_size = int(cfg.get("max_inference_batch_size", 32))
        max_new_tokens = int(cfg.get("max_new_tokens", 256))
        cuda_visible_devices = cfg.get("cuda_visible_devices")

        if cuda_visible_devices is not None:
            os.environ["CUDA_VISIBLE_DEVICES"] = str(cuda_visible_devices)

        dtype = {
            "float32": torch.float32,
            "float16": torch.float16,
            "bfloat16": torch.bfloat16,
        }.get(dtype_name)
        if dtype is None:
            raise ValueError(f"unsupported qwen3-asr dtype: {dtype_name}")

        logger.info(
            "Loading qwen3-asr model=%s path=%s device_map=%s dtype=%s "
            "max_inference_batch_size=%s max_new_tokens=%s",
            self.model_name,
            model_path,
            device_map,
            dtype_name,
            max_inference_batch_size,
            max_new_tokens,
        )
        recognizer = Qwen3ASRModel.from_pretrained(
            model_path,
            dtype=dtype,
            device_map=device_map,
            max_inference_batch_size=max_inference_batch_size,
            max_new_tokens=max_new_tokens,
        )
        logger.info("qwen3-asr model loaded.")
        return recognizer

    def _transcribe_impl(
        self,
        audio_path: str,
        language: str | None,
        hotwords: list[str],
        enable_itn: bool,
    ) -> str:
        if self.model_handle is None:
            raise RuntimeError("qwen3-asr model is not loaded")

        waveform, _ = librosa.load(
            str(Path(audio_path)),
            sr=self._sample_rate,
            mono=True,
        )
        qwen_language = _resolve_qwen_language(language)
        result = self.model_handle.transcribe(
            audio=(waveform.astype(np.float32), self._sample_rate),
            language=qwen_language,
        )
        return _normalize_text(_extract_text(result))

    def _create_stream_session_impl(
        self,
        file_name: str,
        language: str | None,
        hotwords: list[str],
        enable_itn: bool,
        sample_rate: int,
        channels: int,
        audio_format: str,
    ):
        min_decode_ms = max(100, int(self.runtime_options.get("qwen_min_decode_ms", 240)))
        return {
            "file_name": file_name,
            "language": language,
            "hotwords": hotwords,
            "enable_itn": enable_itn,
            "sample_rate": sample_rate or self._sample_rate,
            "channels": channels,
            "audio_format": audio_format,
            "audio_buffer": np.empty(0, dtype=np.float32),
            "audio_chunks": [],
            "pending_samples": 0,
            "last_text": "",
            "min_decode_ms": min_decode_ms,
            "qwen_language": _resolve_qwen_language(language),
        }

    def _merged_audio(self, session) -> np.ndarray:
        if session["audio_chunks"]:
            if session["audio_buffer"].size == 0:
                session["audio_buffer"] = np.concatenate(session["audio_chunks"])
            else:
                session["audio_buffer"] = np.concatenate([session["audio_buffer"], *session["audio_chunks"]])
            session["audio_chunks"].clear()
        return session["audio_buffer"]

    def _reset_stream_session(self, session) -> None:
        session["audio_buffer"] = np.empty(0, dtype=np.float32)
        session["audio_chunks"].clear()
        session["pending_samples"] = 0
        session["last_text"] = ""

    def _transcribe_stream_chunk_impl(
        self,
        session,
        audio_chunk: bytes,
        is_final: bool,
    ) -> str:
        if self.model_handle is None:
            return ""
        if not audio_chunk and not is_final:
            return ""

        if audio_chunk:
            samples = np.frombuffer(audio_chunk, dtype=np.int16).astype(np.float32) / 32768.0
            if samples.size:
                session["audio_chunks"].append(samples)
                session["pending_samples"] += int(samples.size)

        min_decode_samples = int(self._sample_rate * session["min_decode_ms"] / 1000)
        should_decode = is_final or session["pending_samples"] >= min_decode_samples
        if not should_decode:
            return ""

        merged_audio = self._merged_audio(session)
        if merged_audio.size == 0:
            return ""

        try:
            result = self.model_handle.transcribe(
                audio=(merged_audio.copy(), self._sample_rate),
                language=session.get("qwen_language"),
            )
        except Exception as exc:
            logger.error("qwen3-asr transcribe failed: %s", exc, exc_info=True)
            return ""

        current_text = _normalize_text(_extract_text(result))
        if not current_text:
            logger.info(
                "qwen3-asr returned empty text. is_final=%s pending_samples=%s merged_samples=%s language=%s result_type=%s result_preview=%r",
                is_final,
                session["pending_samples"],
                int(merged_audio.size),
                session.get("qwen_language"),
                type(result).__name__,
                str(result)[:300],
            )
        new_text = _delta_text(session["last_text"], current_text)
        session["last_text"] = current_text
        session["pending_samples"] = 0

        if is_final:
            self._reset_stream_session(session)

        return new_text
