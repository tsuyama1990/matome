from typing import Final

from pydantic import BaseModel, ConfigDict


class TestConfig(BaseModel):
    """Configuration for tests."""

    model_config = ConfigDict(frozen=True)

    NUM_THREADS: int = 4
    CHUNKS_PER_THREAD: int = 25
    READ_LOOPS: int = 10
    WRITE_LOOPS: int = 10

    @property
    def total_chunks(self) -> int:
        return self.NUM_THREADS * self.CHUNKS_PER_THREAD

# Global test config instance
TEST_CONFIG: Final[TestConfig] = TestConfig()
