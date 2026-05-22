from backend.src.core.config import settings
from backend.src.core.logging_config import get_logger
from backend.src.services.streaming_vad import StreamingVadProvider
from backend.src.services.vad_service import BaseVadProvider, NoopVadProvider

logger = get_logger(__name__)


def build_vad_provider() -> BaseVadProvider:
    backend_name = (settings.vad_backend or "noop").lower()

    if backend_name == "noop":
        logger.info("Using Noop VAD provider.")
        return NoopVadProvider()

    if backend_name in {"streaming", "model", "funasr"}:
        if not settings.vad_model_path:
            raise ValueError("vad_model_path is required when VAD_BACKEND uses model-based VAD")
        logger.info(
            "Using streaming VAD provider. backend=%s model_path=%s device=%s",
            backend_name,
            settings.vad_model_path,
            settings.vad_device,
        )
        return StreamingVadProvider(
            model_path=settings.vad_model_path,
            device=settings.vad_device,
            energy_threshold=settings.vad_energy_threshold,
        )

    raise ValueError(
        f"unsupported vad backend: {backend_name}. "
        "Implement your provider in backend.src.services.vad_provider.build_vad_provider()."
    )
