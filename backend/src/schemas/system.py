from pydantic import BaseModel, Field


class ModelRuntimeConfig(BaseModel):
    engine: str
    path: str | None = None
    device: str = "auto"
    enabled: bool = True
    auto_load: bool = False
    options: dict = Field(default_factory=dict)


class LoadedModelInfo(BaseModel):
    model_name: str
    engine_name: str
    loaded: bool
    model_path: str | None = None
    device: str = "auto"


class GpuUsage(BaseModel):
    available: bool = False
    name: str | None = None
    used_mb: float = 0.0
    total_mb: float = 0.0
    utilization_percent: float = 0.0


class MemoryUsage(BaseModel):
    used_percent: float
    used_mb: float
    total_mb: float


class CpuUsage(BaseModel):
    used_percent: float


class SystemHealth(BaseModel):
    status: str
    loaded_models: list[LoadedModelInfo]
    configured_models: list[str]
    cpu: CpuUsage
    memory: MemoryUsage
    gpu: GpuUsage
