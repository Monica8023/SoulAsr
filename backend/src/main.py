from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from backend.src.api.v1.asr import router as asr_router
from backend.src.api.v1.models import router as models_router
from backend.src.api.v1.system import router as system_router
from backend.src.core.config import settings
from backend.src.core.logging_config import setup_logging
from backend.src.schemas.common import ApiResponse
from backend.src.services.model_manager import model_manager


@asynccontextmanager
async def lifespan(_: FastAPI):
    setup_logging()
    model_manager.refresh_registry()
    model_manager.ensure_default_model_loaded()
    yield
    model_manager.unload_all()


app = FastAPI(
    title=settings.project_name,
    version=settings.app_version,
    lifespan=lifespan,
)

app.include_router(asr_router, prefix=f"{settings.api_v1_prefix}/asr", tags=["asr"])
app.include_router(
    models_router,
    prefix=f"{settings.api_v1_prefix}/models",
    tags=["models"],
)
app.include_router(
    system_router,
    prefix=f"{settings.api_v1_prefix}/system",
    tags=["system"],
)


@app.exception_handler(ValueError)
async def handle_value_error(_: Request, exc: ValueError):
    payload = ApiResponse(code=400, message=str(exc), data=None)
    return JSONResponse(status_code=400, content=payload.model_dump())


@app.get("/health", tags=["system"])
def health_check():
    return {"status": "ok", "service": settings.project_name, "version": settings.app_version}
