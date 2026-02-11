import pytest
from pydantic import ValidationError

from domain_models.config import ProcessingConfig, ProcessingMode


def test_config_mode_defaults() -> None:
    """Test default processing mode."""
    config = ProcessingConfig()
    assert config.processing_mode == ProcessingMode.DEFAULT


def test_config_mode_dikw() -> None:
    """Test DIKW processing mode."""
    config = ProcessingConfig(processing_mode=ProcessingMode.DIKW)
    assert config.processing_mode == ProcessingMode.DIKW


def test_config_mode_invalid() -> None:
    """Test invalid processing mode."""
    with pytest.raises(ValidationError):
        ProcessingConfig(processing_mode="invalid")  # type: ignore[arg-type]
