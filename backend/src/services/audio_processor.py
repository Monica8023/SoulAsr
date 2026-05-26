from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf

from backend.src.core.config import settings
from backend.src.utils.file_ops import cleanup_file, ensure_dir, unique_file_path


@dataclass
class PreparedAudio:
    source_path: str
    normalized_path: str
    file_name: str
    suffix: str
    audio_seconds: float | None
    file_size_bytes: int
    source_sample_rate: int | None
    source_channels: int | None
    target_sample_rate: int
    target_channels: int
    cleanup_paths: list[str]


@dataclass
class StreamChunkInfo:
    audio_bytes: bytes
    sample_rate: int
    channels: int
    audio_format: str
    duration_seconds: float | None


class AudioProcessor:
    def __init__(self):
        ensure_dir(settings.temp_dir)

    def prepare_audio_path(self, audio_path: str) -> PreparedAudio:
        path = Path(audio_path)
        if not path.exists():
            raise FileNotFoundError(f"audio file not found: {audio_path}")
        return self._normalize_audio_file(
            source_path=path,
            file_name=path.name,
            cleanup_paths=[],
        )

    def persist_bytes(self, file_name: str, audio_bytes: bytes) -> PreparedAudio:
        suffix = Path(file_name).suffix or ".wav"
        target = unique_file_path(settings.temp_dir, suffix=suffix)
        Path(target).write_bytes(audio_bytes)
        return self._normalize_audio_file(
            source_path=Path(target),
            file_name=file_name,
            cleanup_paths=[target],
        )

    def cleanup_prepared_audio(self, prepared_audio: PreparedAudio):
        for path in prepared_audio.cleanup_paths:
            cleanup_file(path)

    def estimate_duration_from_bytes(
        self,
        audio_bytes: bytes,
        audio_seconds: float | None = None,
    ) -> float | None:
        if audio_seconds is not None:
            return audio_seconds
        if not audio_bytes:
            return 0.0
        # 16kHz, mono, 16-bit PCM fallback estimate
        return round(len(audio_bytes) / 32000, 4)

    def normalize_stream_chunk(
        self,
        audio_bytes: bytes,
        sample_rate: int,
        channels: int,
        audio_format: str,
    ) -> StreamChunkInfo:
        format_key = (audio_format or "pcm_s16le").lower()

        if format_key != "pcm_s16le":
            duration = self.estimate_duration_from_bytes(audio_bytes=audio_bytes)
            return StreamChunkInfo(
                audio_bytes=audio_bytes,
                sample_rate=sample_rate,
                channels=channels,
                audio_format=format_key,
                duration_seconds=duration,
            )

        waveform = np.frombuffer(audio_bytes, dtype=np.int16)
        if waveform.size == 0:
            return StreamChunkInfo(
                audio_bytes=b"",
                sample_rate=settings.target_sample_rate,
                channels=settings.target_channels,
                audio_format="pcm_s16le",
                duration_seconds=0.0,
            )

        effective_channels = max(1, channels)
        if effective_channels > 1:
            frame_count = waveform.size // effective_channels
            waveform = waveform[: frame_count * effective_channels].reshape(frame_count, effective_channels)
            waveform = waveform.mean(axis=1)
        else:
            waveform = waveform.astype(np.float32)

        waveform = waveform.astype(np.float32) / 32768.0
        effective_sample_rate = sample_rate or settings.target_sample_rate
        if effective_sample_rate != settings.target_sample_rate:
            waveform = librosa.resample(
                waveform,
                orig_sr=effective_sample_rate,
                target_sr=settings.target_sample_rate,
            )

        waveform = np.clip(waveform, -1.0, 1.0)
        pcm16 = (waveform * 32767.0).astype(np.int16).tobytes()
        duration = (
            round(len(pcm16) / (2 * settings.target_sample_rate * settings.target_channels), 4)
            if pcm16
            else 0.0
        )
        return StreamChunkInfo(
            audio_bytes=pcm16,
            sample_rate=settings.target_sample_rate,
            channels=settings.target_channels,
            audio_format="pcm_s16le",
            duration_seconds=duration,
        )

    def _normalize_audio_file(
        self,
        source_path: Path,
        file_name: str,
        cleanup_paths: list[str],
    ) -> PreparedAudio:
        suffix = source_path.suffix.lower()
        source_info = self._inspect_audio(source_path)

        waveform, _ = librosa.load(
            str(source_path),
            sr=settings.target_sample_rate,
            mono=settings.target_channels == 1,
        )

        normalized_path = unique_file_path(
            settings.temp_dir,
            suffix=settings.normalized_audio_suffix,
        )
        sf.write(
            normalized_path,
            waveform,
            settings.target_sample_rate,
            subtype="PCM_16",
        )

        duration = (
            round(len(waveform) / settings.target_sample_rate, 4)
            if settings.target_sample_rate > 0
            else None
        )
        return PreparedAudio(
            source_path=str(source_path),
            normalized_path=normalized_path,
            file_name=file_name,
            suffix=suffix,
            audio_seconds=duration,
            file_size_bytes=source_path.stat().st_size if source_path.exists() else 0,
            source_sample_rate=source_info["sample_rate"],
            source_channels=source_info["channels"],
            target_sample_rate=settings.target_sample_rate,
            target_channels=settings.target_channels,
            cleanup_paths=[*cleanup_paths, normalized_path],
        )

    def _inspect_audio(self, source_path: Path) -> dict[str, int | None]:
        try:
            info = sf.info(str(source_path))
            return {
                "sample_rate": info.samplerate,
                "channels": info.channels,
            }
        except Exception:
            return {
                "sample_rate": None,
                "channels": None,
            }
