from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar


class BaseEngine(ABC):
    registry: ClassVar[dict[str, type["BaseEngine"]]] = {}
    engine_name: ClassVar[str | None] = None

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if cls.engine_name:
            BaseEngine.registry[cls.engine_name] = cls

    def __init__(
        self,
        model_name: str,
        model_path: str | None = None,
        device: str = "auto",
        runtime_options: dict[str, Any] | None = None,
    ):
        self.model_name = model_name
        self.model_path = model_path
        self.device = device
        self.runtime_options = runtime_options or {}
        self.loaded = False
        self.model_handle: Any = None

    @classmethod
    def get_registry(cls) -> dict[str, type["BaseEngine"]]:
        return dict(cls.registry)

    def load(self):
        if self.loaded:
            return self.model_handle
        self.model_handle = self._load_model()
        self.loaded = True
        return self.model_handle

    def unload(self):
        self._unload_model()
        self.model_handle = None
        self.loaded = False

    def transcribe(
        self,
        audio_path: str,
        language: str | None = None,
        hotwords: list[str] | None = None,
        enable_itn: bool = False,
    ) -> str:
        self.load()
        return self._transcribe_impl(
            audio_path=audio_path,
            language=language,
            hotwords=hotwords or [],
            enable_itn=enable_itn,
        )

    def transcribe_bytes(
        self,
        audio_bytes: bytes,
        file_name: str,
        language: str | None = None,
        hotwords: list[str] | None = None,
        enable_itn: bool = False,
    ) -> str:
        self.load()
        return self._transcribe_bytes_impl(
            audio_bytes=audio_bytes,
            file_name=file_name,
            language=language,
            hotwords=hotwords or [],
            enable_itn=enable_itn,
        )

    def create_stream_session(
        self,
        file_name: str,
        language: str | None = None,
        hotwords: list[str] | None = None,
        enable_itn: bool = False,
        sample_rate: int = 16000,
        channels: int = 1,
        audio_format: str = "pcm_s16le",
    ):
        self.load()
        return self._create_stream_session_impl(
            file_name=file_name,
            language=language,
            hotwords=hotwords or [],
            enable_itn=enable_itn,
            sample_rate=sample_rate,
            channels=channels,
            audio_format=audio_format,
        )

    def transcribe_stream_chunk(
        self,
        session,
        audio_chunk: bytes,
        is_final: bool = False,
    ) -> str:
        self.load()
        return self._transcribe_stream_chunk_impl(
            session=session,
            audio_chunk=audio_chunk,
            is_final=is_final,
        )

    @abstractmethod
    def _load_model(self):
        raise NotImplementedError

    def _unload_model(self):
        return None

    @abstractmethod
    def _transcribe_impl(
        self,
        audio_path: str,
        language: str | None,
        hotwords: list[str],
        enable_itn: bool,
    ) -> str:
        raise NotImplementedError

    def _transcribe_bytes_impl(
        self,
        audio_bytes: bytes,
        file_name: str,
        language: str | None,
        hotwords: list[str],
        enable_itn: bool,
    ) -> str:
        return self._transcribe_impl(
            audio_path=file_name,
            language=language,
            hotwords=hotwords,
            enable_itn=enable_itn,
        )

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
        return {
            "file_name": file_name,
            "language": language,
            "hotwords": hotwords,
            "enable_itn": enable_itn,
            "sample_rate": sample_rate,
            "channels": channels,
            "audio_format": audio_format,
            "chunks": [],
        }

    def _process_stream_chunk_impl(self, session, audio_chunk: bytes) -> str | None:
        session["chunks"].append(audio_chunk)
        return None

    def _transcribe_stream_chunk_impl(
        self,
        session,
        audio_chunk: bytes,
        is_final: bool,
    ) -> str:
        if audio_chunk:
            self._process_stream_chunk_impl(session=session, audio_chunk=audio_chunk)
        if not is_final:
            return ""
        result = self._transcribe_bytes_impl(
            audio_bytes=b"".join(session["chunks"]),
            file_name=session["file_name"],
            language=session["language"],
            hotwords=session["hotwords"],
            enable_itn=session["enable_itn"],
        )
        session["chunks"] = []
        return result
