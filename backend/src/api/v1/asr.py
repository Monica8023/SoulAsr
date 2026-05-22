from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, UploadFile, WebSocket

from backend.src.api.deps import get_asr_service
from backend.src.schemas.asr import BatchTranscriptionRequest, TranscriptionRequest
from backend.src.schemas.batch import BatchTaskCreateResponse, BatchTaskResultResponse, BatchTaskStatusResponse
from backend.src.schemas.common import ApiResponse

router = APIRouter()


@router.post("/transcribe")
def transcribe(payload: TranscriptionRequest, service=Depends(get_asr_service)):
    result = service.transcribe(payload)
    return ApiResponse(message="transcription complete", data=result.model_dump())


@router.post("/batch")
def batch_transcribe(payload: BatchTranscriptionRequest, service=Depends(get_asr_service)):
    result = service.transcribe_batch(payload)
    return ApiResponse(message="batch transcription complete", data=result.model_dump())


@router.post("/batch/tasks", response_model=ApiResponse)
async def create_batch_task(
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
    model_name: str | None = Form(default=None),
    language: str | None = Form(default=None),
    hotwords: str | None = Form(default=None),
    enable_itn: bool = Form(default=False),
    push_by_realtime: bool = Form(default=False),
    service=Depends(get_asr_service),
):
    payload = BatchTranscriptionRequest(
        model_name=model_name,
        options={
            "language": language,
            "hotwords": [item.strip() for item in (hotwords or "").split(",") if item.strip()],
            "enable_itn": enable_itn,
            "push_by_realtime": push_by_realtime,
        },
    )
    result: BatchTaskCreateResponse = await service.create_batch_task(
        files=files,
        model_name=model_name,
        options=payload.options,
        background_tasks=background_tasks,
    )
    return ApiResponse(message="batch task accepted", data=result.model_dump())


@router.get("/batch/tasks/{task_id}")
def get_batch_task_status(task_id: str, service=Depends(get_asr_service)):
    result: BatchTaskStatusResponse = service.get_batch_task_status(task_id)
    return ApiResponse(data=result.model_dump())


@router.get("/batch/tasks/{task_id}/result")
def get_batch_task_result(task_id: str, service=Depends(get_asr_service)):
    result: BatchTaskResultResponse = service.get_batch_task_result(task_id)
    return ApiResponse(data=result.model_dump())


@router.websocket("/stream")
async def stream_transcribe(websocket: WebSocket, service=Depends(get_asr_service)):
    await service.handle_streaming_session(websocket)
