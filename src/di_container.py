import importlib
from collections.abc import Callable
from typing import Any

from src.domain_models.config import PipelineConfig
from src.infrastructure.interfaces import AbstractLLMGateway, AbstractVectorRepository


class ProductionDIContainer:
    def __init__(
        self,
        config: PipelineConfig,
        llm_gateway_factory: Callable[[], AbstractLLMGateway] | None = None,
        vector_repo_factory: Callable[[], AbstractVectorRepository] | None = None,
    ) -> None:
        self.config = config
        self.llm_gateway_factory = llm_gateway_factory
        self.vector_repo_factory = vector_repo_factory

    def _validate_instance(self, instance: Any, expected_type: type[Any]) -> None:
        if not isinstance(instance, expected_type):
            msg = f"Resolved object {instance} is not an instance of {expected_type}"
            raise TypeError(msg)

    def _resolve_service(self, path: str, expected_type: type[Any]) -> Any:
        try:
            module_name, class_name = path.rsplit(".", 1)
            module = importlib.import_module(module_name)
            service_class = getattr(module, class_name)
            instance = service_class()
            self._validate_instance(instance, expected_type)
        except (ImportError, AttributeError, ValueError, TypeError) as err:
            msg = f"Failed to resolve service at path {path}"
            raise ImportError(msg) from err
        else:
            return instance
