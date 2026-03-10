import os
from pathlib import Path

from src.config import ModeConfig, Settings, create_app_context


def test_settings_default(tmp_path: Path) -> None:
    os.environ["MODE"] = "cli"
    os.environ["TEXT_FAST_MODEL"] = "google/gemini-2.5-flash"
    os.environ["TEXT_REASONING_MODEL"] = "deepseek/deepseek-reasoner"
    os.environ["MULTIMODAL_MODEL"] = "openai/gpt-4o"
    os.environ["MATOME_BASE_DATA_DIR"] = str(tmp_path)
    dummy_cert = tmp_path / "dummy.pem"
    dummy_cert.write_text("cert")

    from src.config import AIConfig, FileProcessingConfig, MLConfig, PipelineConfig, SecurityConfig

    try:
        from src.config import (
            AIConfig,
            FileProcessingConfig,
            MLConfig,
            PipelineConfig,
            SecurityConfig,
        )

        settings = Settings(
            ai=AIConfig(
                text_fast_model="google/gemini-2.5-flash",
                text_reasoning_model="deepseek/deepseek-reasoner",
                multimodal_model="openai/gpt-4o",
            ),
            file=FileProcessingConfig(
                allowed_base_dir=str(tmp_path),
                chunk_size=1000,
                chunk_overlap=100,
            ),
            ml=MLConfig(
                spacy_model="en_core_web_sm",
                trusted_spacy_models=["en_core_web_sm", "en_core_web_md"],
            ),
            security=SecurityConfig(),
            pipeline=PipelineConfig(),
        )
        mode_config = ModeConfig()
        assert mode_config.mode == "cli"
        assert settings.ai.text_fast_model == "google/gemini-2.5-flash"
    finally:
        del os.environ["MODE"]
        del os.environ["TEXT_FAST_MODEL"]
        del os.environ["TEXT_REASONING_MODEL"]
        del os.environ["MULTIMODAL_MODEL"]


def test_app_context_creation(tmp_path: Path) -> None:
    os.environ["MODE"] = "test"
    os.environ["TEXT_FAST_MODEL"] = "google/gemini-2.5-flash"
    os.environ["TEXT_REASONING_MODEL"] = "deepseek/deepseek-reasoner"
    os.environ["MULTIMODAL_MODEL"] = "openai/gpt-4o"
    os.environ["MATOME_BASE_DATA_DIR"] = str(tmp_path)
    dummy_cert = tmp_path / "dummy.pem"
    dummy_cert.write_text("cert")

    try:
        from src.config import (
            AIConfig,
            FileProcessingConfig,
            MLConfig,
            PipelineConfig,
            SecurityConfig,
        )

        settings = Settings(
            ai=AIConfig(
                text_fast_model="google/gemini-2.5-flash",
                text_reasoning_model="deepseek/deepseek-reasoner",
                multimodal_model="openai/gpt-4o",
            ),
            file=FileProcessingConfig(
                allowed_base_dir=str(tmp_path),
                chunk_size=1000,
                chunk_overlap=100,
            ),
            ml=MLConfig(
                spacy_model="en_core_web_sm",
                trusted_spacy_models=["en_core_web_sm", "en_core_web_md"],
            ),
            security=SecurityConfig(),
            pipeline=PipelineConfig(),
        )
        mode_config = ModeConfig()
        from src.config import DatabaseContext

        context = create_app_context(settings, mode_config)
        db_context = DatabaseContext()
        assert context.mode_config.mode == "test"
        assert context.settings is settings
        assert db_context.db is None
    finally:
        del os.environ["MODE"]
        del os.environ["TEXT_FAST_MODEL"]
        del os.environ["TEXT_REASONING_MODEL"]
        del os.environ["MULTIMODAL_MODEL"]
