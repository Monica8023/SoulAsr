from fastapi import APIRouter, Depends

from backend.src.api.deps import get_model_manager
from backend.src.schemas.common import ApiResponse
from backend.src.schemas.metrics import ModelLoadRequest

router = APIRouter()


@router.get("")
def list_models(manager=Depends(get_model_manager)):
    loaded_models = manager.list_loaded_models()
    data = {
        "available_models": manager.list_supported_models(),
        "disabled_models": manager.list_disabled_models(),
        "loaded_models": [item.model_dump() for item in loaded_models],
        "current_model": loaded_models[0].model_name if loaded_models else None,
    }
    return ApiResponse(data=data)


@router.post("/load")
def load_model(payload: ModelLoadRequest, manager=Depends(get_model_manager)):
    engine = manager.load_model(payload.model_name)
    return ApiResponse(
        message="model loaded",
        data={
            "model_name": payload.model_name,
            "engine_name": engine.engine_name,
            "loaded": engine.loaded,
            "model_path": engine.model_path,
        },
    )


@router.delete("/{model_name}")
def unload_model(model_name: str, manager=Depends(get_model_manager)):
    manager.unload_model(model_name)
    return ApiResponse(message="model unloaded", data={"model_name": model_name})


@router.post("/unload")
def unload_current_model(manager=Depends(get_model_manager)):
    loaded_models = manager.list_loaded_models()
    if loaded_models:
        manager.unload_model(loaded_models[0].model_name)
    return ApiResponse(message="model unloaded", data={"current_model": None})


@router.get("/health")
def model_health(manager=Depends(get_model_manager)):
    loaded_models = manager.list_loaded_models()
    payload = {
        "current_model": loaded_models[0].model_name if loaded_models else None,
        "loaded": bool(loaded_models),
        "supported_models": manager.list_supported_models(),
        "disabled_models": manager.list_disabled_models(),
        "loaded_models": [item.model_dump() for item in loaded_models],
    }
    return ApiResponse(data=payload)


@router.post("/refresh")
def refresh_registry(manager=Depends(get_model_manager)):
    manager.refresh_registry()
    return ApiResponse(
        message="model registry refreshed",
        data={
            "available_models": manager.list_supported_models(),
            "disabled_models": manager.list_disabled_models(),
        },
    )
