from abc import ABC, abstractmethod


class AbstractVectorRepository(ABC):
    @abstractmethod
    def health_check(self) -> bool:
        pass


class AbstractLLMGateway(ABC):
    @abstractmethod
    def health_check(self) -> bool:
        pass
