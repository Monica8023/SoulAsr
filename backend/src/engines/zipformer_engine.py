import numpy as np

from backend.src.core.logging_config import get_logger
from backend.src.engines.base_engine import BaseEngine

logger = get_logger(__name__)


class ZipformerEngine(BaseEngine):
    engine_name = "zipformer"

    def _load_model(self):
        try:
            import sherpa_onnx
        except ImportError as exc:
            raise RuntimeError(
                "Failed to import sherpa_onnx. This is usually caused by an incompatible "
                "Windows wheel/DLL architecture or missing runtime dependency."
            ) from exc

        cfg = self.runtime_options
        model_dir = str(self.model_path)
        encoder = cfg.get("encoder", cfg.get("asr_encoder", f"{model_dir}/encoder.int8.onnx"))
        decoder = cfg.get("decoder", cfg.get("asr_decoder", f"{model_dir}/decoder.onnx"))
        joiner = cfg.get("joiner", cfg.get("asr_joiner", f"{model_dir}/joiner.int8.onnx"))
        tokens = cfg.get("tokens", cfg.get("asr_tokens", f"{model_dir}/tokens.txt"))
        num_threads = cfg.get("num_threads", cfg.get("asr_num_threads", 2))
        feature_dim = cfg.get("feature_dim", cfg.get("asr_feature_dim", 80))
        sample_rate = cfg.get("sample_rate", cfg.get("asr_sample_rate", 16000))
        provider = cfg.get("provider", cfg.get("asr_provider", "cuda"))
        decoding_method = cfg.get("decoding_method")
        hotwords_file = cfg.get("hotwords_file")
        hotwords_score = cfg.get("hotwords_score")
        modeling_unit = cfg.get("modeling_unit")
        bpe_vocab = cfg.get("bpe_vocab", f"{model_dir}/bpe.vocab")

        logger.info(
            "Loading Zipformer model=%s encoder=%s decoder=%s joiner=%s tokens=%s "
            "num_threads=%s feature_dim=%s sample_rate=%s provider=%s",
            self.model_name,
            encoder,
            decoder,
            joiner,
            tokens,
            num_threads,
            feature_dim,
            sample_rate,
            provider,
        )

        recognizer_kwargs = {
            "tokens": tokens,
            "encoder": encoder,
            "decoder": decoder,
            "joiner": joiner,
            "num_threads": num_threads,
            "sample_rate": sample_rate,
            "feature_dim": feature_dim,
            "provider": provider,
        }
        if decoding_method:
            recognizer_kwargs["decoding_method"] = decoding_method
        if hotwords_file:
            recognizer_kwargs["hotwords_file"] = hotwords_file
        if hotwords_score is not None:
            recognizer_kwargs["hotwords_score"] = hotwords_score
        if modeling_unit:
            recognizer_kwargs["modeling_unit"] = modeling_unit
        if modeling_unit and "bpe" in modeling_unit and bpe_vocab:
            recognizer_kwargs["bpe_vocab"] = bpe_vocab

        recognizer = sherpa_onnx.OnlineRecognizer.from_transducer(**recognizer_kwargs)
        logger.info("Zipformer model loaded.")
        return recognizer

    def _unload_model(self):
        logger.info("Unloading Zipformer model=%s", self.model_name)

    def _transcribe_impl(
        self,
        audio_path: str,
        language: str | None,
        hotwords: list[str],
        enable_itn: bool,
    ) -> str:
        hotword_text = f", hotwords={','.join(hotwords)}" if hotwords else ""
        return (
            f"[zipformer|lang={language or 'auto'}|itn={enable_itn}] "
            f"placeholder transcript for {audio_path}{hotword_text}"
        )

    def _create_stream_session_impl(
        self,
        file_name: str,
        language: str | None,
        hotwords: list[str],
        enable_itn: bool,
        sample_rate: int,
        channels: int,
        audio_format: str,
    ):
        if self.model_handle is None:
            raise RuntimeError("Zipformer recognizer is not loaded")

        session_sample_rate = int(sample_rate or self.runtime_options.get("sample_rate", 16000))
        if channels != 1:
            logger.warning(
                "Zipformer streaming expects mono PCM. model=%s file=%s channels=%s",
                self.model_name,
                file_name,
                channels,
            )

        return {
            "stream": self.model_handle.create_stream(),
            "file_name": file_name,
            "language": language,
            "hotwords": hotwords,
            "enable_itn": enable_itn,
            "sample_rate": session_sample_rate,
            "channels": channels,
            "audio_format": audio_format,
            "last_text": "",
        }

    def _decode_stream_incremental_text(self, session) -> str:
        if self.model_handle is None:
            return ""

        stream = session["stream"]
        while self.model_handle.is_ready(stream):
            self.model_handle.decode_stream(stream)

        current_text = self.model_handle.get_result(stream)
        last_text = session.get("last_text", "")
        if not isinstance(current_text, str):
            current_text = str(current_text or "")

        if not current_text.startswith(last_text):
            # Some runtimes may revise the partial hypothesis. Fall back to
            # returning the full current text so the caller can still surface it.
            new_text = current_text
        else:
            new_text = current_text[len(last_text) :]

        session["last_text"] = current_text
        return new_text

    def _reset_stream_session(self, session) -> None:
        if self.model_handle is None:
            return

        self.model_handle.reset(session["stream"])
        session["last_text"] = ""

    def _transcribe_stream_chunk_impl(
        self,
        session,
        audio_chunk: bytes,
        is_final: bool,
    ) -> str:
        if self.model_handle is None:
            return ""

        if not audio_chunk and not is_final:
            return ""

        if audio_chunk:
            samples = np.frombuffer(audio_chunk, dtype=np.int16).astype(np.float32) / 32768.0
            session["stream"].accept_waveform(session["sample_rate"], samples)

        new_text = self._decode_stream_incremental_text(session)

        if is_final:
            self._reset_stream_session(session)

        return new_text
