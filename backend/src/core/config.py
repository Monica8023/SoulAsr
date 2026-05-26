from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_model_registry_path() -> str:
    return str(_project_root() / "backend" / "config" / "model_registry.example.json")


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _default_onnxruntime_dll_dir() -> str:
    return str(_project_root() / "backend" / "vendor" / "onnxruntime")


def _default_env_file() -> str:
    return str(_project_root() / "backend" / ".env")


class Settings(BaseSettings):
    project_name: str = "ASR Test Platform"
    app_version: str = "0.1.0"
    api_v1_prefix: str = "/api/v1"
    host: str = "0.0.0.0"
    port: int = 8000
    default_model: str = "whisper"
    model_root: str = "./models"
    model_registry_path: str = _default_model_registry_path()
    auto_load_default_model: bool = False
    auto_load_on_request: bool = True
    temp_dir: str = "./backend/tmp"
    target_sample_rate: int = 16000
    target_channels: int = 1
    normalized_audio_suffix: str = ".wav"
    vad_backend: str = "noop"
    vad_model_path: str | None = None
    vad_device: str = "cpu"
    vad_energy_threshold: int = 1500
    simulated_stream_chunk_count: int = 3
    simulated_stream_min_delay_ms: int = 120
    onnxruntime_dll_dir: str | None = _default_onnxruntime_dll_dir()
    log_level: str = "INFO"
    log_dir: str = "./backend/logs"
    log_file: str = "app.log"

    model_config = SettingsConfigDict(
        env_file=_default_env_file(),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
