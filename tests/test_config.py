from typing import Final

from pydantic import BaseModel, ConfigDict, Field


class TestConfig(BaseModel):
    """
    Configuration for tests.
    Uses environment variables for overrides, adhering to config best practices.
    """

    model_config = ConfigDict(frozen=True)

    NUM_THREADS: int = Field(default=4, description="Number of threads for concurrency tests")
    CHUNKS_PER_THREAD: int = Field(default=25, description="Chunks per thread")
    READ_LOOPS: int = Field(default=10, description="Number of read loops")
    WRITE_LOOPS: int = Field(default=10, description="Number of write loops")

    @property
    def total_chunks(self) -> int:
        return self.NUM_THREADS * self.CHUNKS_PER_THREAD

# Global test config instance
# Can be overridden by env vars if we used Settings from pydantic-settings,
# but standard BaseModel with defaults is fine for this scope as per existing patterns.
TEST_CONFIG: Final[TestConfig] = TestConfig()
