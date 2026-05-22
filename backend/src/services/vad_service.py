from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from backend.src.core.logging_config import get_logger
from backend.src.services.audio_processor import AudioProcessor

logger = get_logger(__name__)


@dataclass
class VadChunkResult:
    audio_bytes: bytes
    duration_seconds: float
    should_transcribe: bool
    is_sentence_final: bool
    speech_active: bool
    state_changed: bool
    sentence_index: int
    vad_payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class VadSessionState:
    provider_session: Any
    speech_active: bool = False
    speech_seconds: float = 0.0
    sentence_index: int = 0


class BaseVadProvider(ABC):
    @abstractmethod
    def create_session(self) -> Any:
        raise NotImplementedError

    @abstractmethod
    def process_chunk(
        self,
        session: Any,
        audio_bytes: bytes,
        sample_rate: int,
        channels: int,
    ) -> dict[str, Any]:
        raise NotImplementedError

    def finalize_session(self, session: Any) -> dict[str, Any]:
        return {
            "should_transcribe": False,
            "is_sentence_final": False,
        }


class NoopVadProvider(BaseVadProvider):
    def create_session(self) -> dict[str, Any]:
        return {}

    def process_chunk(
        self,
        session: Any,
        audio_bytes: bytes,
        sample_rate: int,
        channels: int,
    ) -> dict[str, Any]:
        return {
            "should_transcribe": bool(audio_bytes),
            "is_sentence_final": False,
            "speech_active": bool(audio_bytes),
        }


class VadService:
    def __init__(
        self,
        audio_processor: AudioProcessor,
        provider: BaseVadProvider | None = None,
    ):
        self.audio_processor = audio_processor
        self.provider = provider or NoopVadProvider()

    def create_session(self) -> VadSessionState:
        provider_session = self.provider.create_session()
        logger.info("VAD session created. provider=%s", self.provider.__class__.__name__)
        return VadSessionState(provider_session=provider_session)

    def process_realtime_chunk(
        self,
        session: VadSessionState,
        audio_bytes: bytes,
        sample_rate: int,
        channels: int,
        audio_format: str,
    ) -> VadChunkResult:
        if not isinstance(self.provider, NoopVadProvider) and (audio_format or "").lower() != "pcm_s16le":
            raise ValueError(
                "Realtime VAD requires pcm_s16le audio chunks. "
                f"received audio_format={audio_format!r}"
            )

        previous_speech_active = session.speech_active
        normalized_chunk = self.audio_processor.normalize_stream_chunk(
            audio_bytes=audio_bytes,
            sample_rate=sample_rate,
            channels=channels,
            audio_format=audio_format,
        )
        provider_result = self.provider.process_chunk(
            session=session.provider_session,
            audio_bytes=normalized_chunk.audio_bytes,
            sample_rate=normalized_chunk.sample_rate,
            channels=normalized_chunk.channels,
        )

        should_transcribe = bool(provider_result.get("should_transcribe", bool(normalized_chunk.audio_bytes)))
        is_sentence_final = bool(provider_result.get("is_sentence_final", provider_result.get("is_final", False)))
        speech_active = bool(provider_result.get("speech_active", should_transcribe))

        if previous_speech_active and not speech_active:
            is_sentence_final = True

        if speech_active:
            should_transcribe = True
        elif is_sentence_final:
            should_transcribe = True
        else:
            should_transcribe = bool(provider_result.get("should_transcribe", False))

        session.speech_active = speech_active
        session.speech_seconds += normalized_chunk.duration_seconds or 0.0
        if is_sentence_final:
            session.sentence_index += 1
            session.speech_seconds = 0.0

        forwarded_bytes = normalized_chunk.audio_bytes if speech_active else b""

        return VadChunkResult(
            audio_bytes=forwarded_bytes,
            duration_seconds=normalized_chunk.duration_seconds or 0.0,
            should_transcribe=should_transcribe,
            is_sentence_final=is_sentence_final,
            speech_active=speech_active,
            state_changed=previous_speech_active != speech_active,
            sentence_index=session.sentence_index,
            vad_payload=provider_result,
        )

    def finalize_session(self, session: VadSessionState) -> VadChunkResult:
        provider_result = self.provider.finalize_session(session.provider_session)
        should_transcribe = bool(provider_result.get("should_transcribe", False))
        is_sentence_final = bool(provider_result.get("is_sentence_final", provider_result.get("is_final", False)))
        return VadChunkResult(
            audio_bytes=b"",
            duration_seconds=0.0,
            should_transcribe=should_transcribe,
            is_sentence_final=is_sentence_final,
            speech_active=False,
            state_changed=session.speech_active,
            sentence_index=session.sentence_index + (1 if is_sentence_final else 0),
            vad_payload=provider_result,
        )
