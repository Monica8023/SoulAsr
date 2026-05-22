from backend.src.engines.base_engine import BaseEngine


class FunAsrEngine(BaseEngine):
    engine_name = "funasr"

    def _load_model(self):
        return {
            "backend": "funasr",
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
            f"[funasr|lang={language or 'auto'}|itn={enable_itn}] "
            f"placeholder transcript for {audio_path}{hotword_text}"
        )
