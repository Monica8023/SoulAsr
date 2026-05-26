from pydantic import AliasChoices, BaseModel, Field, model_validator

from backend.src.schemas.metrics import AsrMetrics


class TranscriptionOptions(BaseModel):
    language: str | None = Field(default=None, description="Language code")
    hotwords: list[str] = Field(default_factory=list, description="Hotword list")
    enable_itn: bool = Field(default=False, description="Text normalization switch")
    push_by_realtime: bool = Field(
        default=False,
        description="Whether to simulate realtime stream speed",
    )


class TranscriptionRequest(BaseModel):
    audio_path: str = Field(..., description="Audio file path or storage key")
    model_name: str | None = Field(
        default=None,
        description="Target engine name",
        validation_alias=AliasChoices("model_name", "modelName"),
    )
    options: TranscriptionOptions = Field(default_factory=TranscriptionOptions)

    @model_validator(mode="before")
    @classmethod
    def merge_legacy_fields(cls, data):
        if not isinstance(data, dict):
            return data
        options = dict(data.get("options") or {})
        if "language" in data and "language" not in options:
            options["language"] = data.get("language")
        if "hotwords" in data and "hotwords" not in options:
            hotwords = data.get("hotwords")
            options["hotwords"] = hotwords if isinstance(hotwords, list) else []
        if "enable_itn" in data and "enable_itn" not in options:
            options["enable_itn"] = data.get("enable_itn")
        if "enableItn" in data and "enable_itn" not in options:
            options["enable_itn"] = data.get("enableItn")
        if "push_by_realtime" in data and "push_by_realtime" not in options:
            options["push_by_realtime"] = data.get("push_by_realtime")
        if "pushByRealtime" in data and "push_by_realtime" not in options:
            options["push_by_realtime"] = data.get("pushByRealtime")
        data["options"] = options
        return data


class TranscriptionResponse(BaseModel):
    model_name: str
    audio_path: str
    text: str
    metrics: AsrMetrics


class StreamStartRequest(BaseModel):
    type: str = Field(default="start")
    file_name: str = Field(validation_alias=AliasChoices("file_name", "fileName"))
    model_name: str | None = Field(
        default=None,
        validation_alias=AliasChoices("model_name", "modelName"),
    )
    audio_format: str = Field(
        default="file-bytes",
        validation_alias=AliasChoices("audio_format", "audioFormat"),
    )
    sample_rate: int = Field(
        default=16000,
        validation_alias=AliasChoices("sample_rate", "sampleRate"),
    )
    channels: int = Field(default=1)
    options: TranscriptionOptions = Field(default_factory=TranscriptionOptions)

    @model_validator(mode="before")
    @classmethod
    def merge_stream_legacy_fields(cls, data):
        if not isinstance(data, dict):
            return data
        options = dict(data.get("options") or {})
        if "language" in data and "language" not in options:
            options["language"] = data.get("language")
        if "hotwords" in data and "hotwords" not in options:
            hotwords = data.get("hotwords")
            if isinstance(hotwords, str):
                hotwords = [item.strip() for item in hotwords.split(",") if item.strip()]
            options["hotwords"] = hotwords if isinstance(hotwords, list) else []
        if "enable_itn" in data and "enable_itn" not in options:
            options["enable_itn"] = data.get("enable_itn")
        if "enableItn" in data and "enable_itn" not in options:
            options["enable_itn"] = data.get("enableItn")
        if "push_by_realtime" in data and "push_by_realtime" not in options:
            options["push_by_realtime"] = data.get("push_by_realtime")
        if "pushByRealtime" in data and "push_by_realtime" not in options:
            options["push_by_realtime"] = data.get("pushByRealtime")
        data["options"] = options
        return data


class StreamEndRequest(BaseModel):
    type: str = Field(default="end")


class StreamTextEvent(BaseModel):
    type: str
    text: str
    is_final: bool
    model_name: str
    speech_active: bool | None = None
    sentence_index: int | None = None


class StreamVadEvent(BaseModel):
    type: str = "vad"
    speech_active: bool
    is_sentence_final: bool
    sentence_index: int
    should_transcribe: bool


class StreamMetricsEvent(BaseModel):
    type: str = "metrics"
    rtf: float
    latency_ms: float
    first_token_ms: float
    total_duration_ms: float
    audio_seconds: float | None = None


class StreamErrorEvent(BaseModel):
    type: str = "error"
    code: str
    detail: str
