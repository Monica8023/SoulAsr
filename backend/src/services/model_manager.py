from __future__ import annotations

import json
from logging import Logger
from pathlib import Path
from threading import RLock

from backend.src.core.config import settings
from backend.src.core.logging_config import get_logger
from backend.src.engines import discover_engines
from backend.src.schemas.system import LoadedModelInfo, ModelRuntimeConfig, SystemHealth
from backend.src.services.system_monitor import SystemMonitor


def _default_model_registry() -> dict[str, ModelRuntimeConfig]:
    return {
        "paraformer": ModelRuntimeConfig(engine="paraformer", enabled=False),
        "qwen3-asr": ModelRuntimeConfig(engine="qwen3-asr", enabled=False),
        "zipformer": ModelRuntimeConfig(engine="zipformer", enabled=True),
        "whisper": ModelRuntimeConfig(engine="whisper", enabled=False),
        "funasr": ModelRuntimeConfig(engine="funasr", enabled=False),
    }

class ModelManager:
    def __init__(self):
        self.logger: Logger = get_logger(__name__)
        self._lock = RLock()
        self._engine_factories = discover_engines()
        self._model_configs = self._load_registry()
        self._loaded_engines: dict[str, object] = {}
        self.monitor = SystemMonitor()

    def _load_registry(self) -> dict[str, ModelRuntimeConfig]:
        registry_path = Path(settings.model_registry_path)
        if registry_path.exists():
            raw = json.loads(registry_path.read_text(encoding="utf-8"))
            models = raw.get("models", raw)
            return {
                model_name: ModelRuntimeConfig(**config)
                for model_name, config in models.items()
            }
        return _default_model_registry()

    def refresh_registry(self):
        with self._lock:
            self._engine_factories = discover_engines()
            self._model_configs = self._load_registry()
            enabled_models = [
                model_name for model_name, config in self._model_configs.items()
                if config.enabled
            ]
            disabled_models = [
                model_name for model_name, config in self._model_configs.items()
                if not config.enabled
            ]
            self.logger.info(
                "Model registry refreshed. configured_models=%s enabled_models=%s disabled_models=%s discovered_engines=%s",
                list(self._model_configs.keys()),
                enabled_models,
                disabled_models,
                list(self._engine_factories.keys()),
            )

    def list_supported_models(self) -> list[str]:
        return [
            model_name for model_name, config in self._model_configs.items()
            if config.enabled
        ]

    def list_disabled_models(self) -> list[str]:
        return [
            model_name for model_name, config in self._model_configs.items()
            if not config.enabled
        ]

    def list_loaded_models(self) -> list[LoadedModelInfo]:
        loaded_models: list[LoadedModelInfo] = []
        for model_name, engine in self._loaded_engines.items():
            loaded_models.append(
                LoadedModelInfo(
                    model_name=model_name,
                    engine_name=engine.engine_name or model_name,
                    loaded=engine.loaded,
                    model_path=engine.model_path,
                    device=engine.device,
                )
            )
        return loaded_models

    def get_model_config(self, model_name: str) -> ModelRuntimeConfig:
        if model_name not in self._model_configs:
            raise ValueError(f"unsupported model: {model_name}")
        config = self._model_configs[model_name]
        if not config.enabled:
            raise ValueError(f"model is disabled: {model_name}")
        return config

    def load_model(self, model_name: str):
        with self._lock:
            config = self.get_model_config(model_name)
            engine_class = self._engine_factories.get(config.engine)
            if engine_class is None:
                raise ValueError(f"no engine implementation found for: {config.engine}")

            existing_engine = self._loaded_engines.get(model_name)
            if existing_engine and existing_engine.loaded:
                self.logger.info("Model already loaded. model_name=%s", model_name)
                return existing_engine

            self.logger.info(
                "Loading model. model_name=%s engine=%s path=%s device=%s options=%s",
                model_name,
                config.engine,
                config.path,
                config.device,
                config.options,
            )
            engine = engine_class(
                model_name=model_name,
                model_path=config.path,
                device=config.device,
                runtime_options=config.options,
            )
            engine.load()
            self._loaded_engines[model_name] = engine
            self.logger.info("Model loaded. model_name=%s engine=%s", model_name, config.engine)
            return engine

    def unload_model(self, model_name: str):
        with self._lock:
            engine = self._loaded_engines.pop(model_name, None)
            if engine is not None:
                self.logger.info("Unloading model. model_name=%s", model_name)
                engine.unload()
                self.logger.info("Model unloaded. model_name=%s", model_name)

    def unload_all(self):
        for model_name in list(self._loaded_engines.keys()):
            self.unload_model(model_name)

    def ensure_default_model_loaded(self):
        for model_name, config in self._model_configs.items():
            if config.enabled and config.auto_load:
                self.load_model(model_name)
        if (
            settings.auto_load_default_model
            and settings.default_model in self._model_configs
            and self._model_configs[settings.default_model].enabled
        ):
            self.load_model(settings.default_model)

    def get_engine(self, model_name: str | None = None):
        target_name = model_name or settings.default_model
        if target_name in self._model_configs and not self._model_configs[target_name].enabled:
            raise ValueError(f"model is disabled: {target_name}")
        if target_name in self._loaded_engines:
            return self._loaded_engines[target_name]
        if settings.auto_load_on_request:
            return self.load_model(target_name)
        raise ValueError(f"model is not loaded: {target_name}")

    def get_system_health(self) -> SystemHealth:
        cpu = self.monitor.get_cpu_usage()
        memory = self.monitor.get_memory_usage()
        gpu = self.monitor.get_gpu_usage()
        loaded_models = self.list_loaded_models()
        status = "healthy" if loaded_models else "idle"
        if cpu.used_percent > 90 or gpu.utilization_percent > 95:
            status = "warning"
        return SystemHealth(
            status=status,
            loaded_models=loaded_models,
            configured_models=self.list_supported_models(),
            cpu=cpu,
            memory=memory,
            gpu=gpu,
        )


model_manager = ModelManager()
