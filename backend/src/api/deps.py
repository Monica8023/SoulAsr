from backend.src.services.asr_service import AsrService
from backend.src.services.model_manager import model_manager

asr_service = AsrService(model_manager=model_manager)


def get_model_manager():
    return model_manager


def get_asr_service():
    return asr_service
