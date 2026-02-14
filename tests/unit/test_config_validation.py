import pytest

from domain_models.config import ProcessingConfig
from domain_models.types import DIKWLevel


def test_chunking_consistency_validation() -> None:
    # Valid
    ProcessingConfig(semantic_chunking_mode=True, semantic_chunking_threshold=0.5)

    # Invalid threshold high
    with pytest.raises(ValueError, match="threshold"):
        ProcessingConfig(semantic_chunking_mode=True, semantic_chunking_threshold=1.5)

    # Invalid threshold low
    with pytest.raises(ValueError, match="threshold"):
        ProcessingConfig(semantic_chunking_mode=True, semantic_chunking_threshold=-0.1)

def test_strategy_mapping_default() -> None:
    config = ProcessingConfig()
    assert config.strategy_mapping[DIKWLevel.WISDOM] == "wisdom"
    assert config.strategy_mapping[DIKWLevel.KNOWLEDGE] == "knowledge"
    assert config.strategy_mapping[DIKWLevel.INFORMATION] == "information"

def test_strategy_mapping_custom() -> None:
    custom_map = {DIKWLevel.WISDOM: "custom_wisdom"}
    config = ProcessingConfig(strategy_mapping=custom_map)
    assert config.strategy_mapping[DIKWLevel.WISDOM] == "custom_wisdom"
    # Pydantic doesn't merge dicts by default for fields, it replaces.
    assert DIKWLevel.KNOWLEDGE not in config.strategy_mapping
