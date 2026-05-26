from fastapi import APIRouter, Depends, WebSocket

from backend.src.api.deps import get_asr_service
from backend.src.schemas.asr import TranscriptionRequest
from backend.src.schemas.common import ApiResponse

router = APIRouter()


@router.post("/transcribe")
def transcribe(payload: TranscriptionRequest, service=Depends(get_asr_service)):
    result = service.transcribe(payload)
    return ApiResponse(message="transcription complete", data=result.model_dump())


@router.websocket("/stream")
async def stream_transcribe(websocket: WebSocket, service=Depends(get_asr_service)):
    await service.handle_streaming_session(websocket)
