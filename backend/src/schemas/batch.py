from pydantic import BaseModel, Field

from backend.src.schemas.asr import TranscriptionResponse


class BatchTaskCreateResponse(BaseModel):
    task_id: str
    status: str
    progress: float


class BatchTaskStatusResponse(BaseModel):
    task_id: str
    status: str
    progress: float
    total_files: int
    completed_files: int
    error: str | None = None


class BatchResultItem(BaseModel):
    file_name: str
    text: str
    model_name: str
    total_duration_ms: float
    rtf: float


class BatchTaskResultResponse(BaseModel):
    task_id: str
    status: str
    items: list[BatchResultItem] = Field(default_factory=list)


class BatchTaskRecord(BaseModel):
    task_id: str
    status: str
    progress: float
    total_files: int
    completed_files: int
    error: str | None = None
    items: list[TranscriptionResponse] = Field(default_factory=list)
