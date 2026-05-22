from fastapi import APIRouter, Depends

from backend.src.api.deps import get_model_manager
from backend.src.schemas.common import ApiResponse

router = APIRouter()


@router.get("/health")
def get_system_health(manager=Depends(get_model_manager)):
    health = manager.get_system_health()
    return ApiResponse(data=health.model_dump())
