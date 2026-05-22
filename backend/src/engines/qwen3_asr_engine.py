from backend.src.engines.base_engine import BaseEngine


class Qwen3AsrEngine(BaseEngine):
    engine_name = "qwen3-asr"

    def _load_model(self):
        return {
            "backend": "qwen3-asr",
            "model_path": self.model_path,
            "device": self.device,
            "runtime_options": self.runtime_options,
        }

    def _transcribe_impl(
        self,
        audio_path: str,
        language: str | None,
        hotwords: list[str],
        enable_itn: bool,
    ) -> str:
        hotword_text = f", hotwords={','.join(hotwords)}" if hotwords else ""
        return (
            f"[qwen3-asr|lang={language or 'auto'}|itn={enable_itn}] "
            f"placeholder transcript for {audio_path}{hotword_text}"
        )
