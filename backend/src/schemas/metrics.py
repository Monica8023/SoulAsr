from pydantic import BaseModel


class AsrMetrics(BaseModel):
    latency_ms: float
    rtf: float
    audio_seconds: float | None = None


class ModelLoadRequest(BaseModel):
    model_name: str


class ModelHealth(BaseModel):
    current_model: str | None
    loaded: bool
    supported_models: list[str]
