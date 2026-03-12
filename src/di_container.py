"""Dependency Injection container."""

import importlib
from collections.abc import Callable

from src.domain_models.config import PipelineConfig
from src.infrastructure.interfaces import AbstractLLMGateway, AbstractVectorRepository


class ProductionDIContainer:
    """Dependency injection container."""

    def __init__(
        self,
        config: PipelineConfig,
        llm_gateway_factory: Callable[[], AbstractLLMGateway] | None = None,
        vector_repo_factory: Callable[[], AbstractVectorRepository] | None = None,
    ) -> None:
        """Initialize the DI container."""
        self.config = config

        if llm_gateway_factory:
            self._llm_gateway = llm_gateway_factory()
        else:
            resolved_service = self._resolve_service(config.llm_gateway_path, AbstractLLMGateway)
            if not isinstance(resolved_service, AbstractLLMGateway):
                msg = f"Resolved service {resolved_service} is not an instance of AbstractLLMGateway"
                raise TypeError(msg)
            self._llm_gateway = resolved_service

        if vector_repo_factory:
            self._vector_repo = vector_repo_factory()
        else:
            resolved_repo = self._resolve_service(config.vector_repo_path, AbstractVectorRepository)
            if not isinstance(resolved_repo, AbstractVectorRepository):
                msg = f"Resolved service {resolved_repo} is not an instance of AbstractVectorRepository"
                raise TypeError(msg)
            self._vector_repo = resolved_repo

    def _resolve_service(self, path: str, expected_type: type) -> object:
        """Dynamically resolve a service by import path."""
        try:
            module_name, class_name = path.rsplit(".", 1)
            module = importlib.import_module(module_name)
            service_class = getattr(module, class_name)
            return service_class()
        except (ImportError, AttributeError) as err:
            msg = f"Failed to load service from {path}"
            raise ImportError(msg) from err

    @property
    def llm_gateway(self) -> AbstractLLMGateway:
        """Get the LLM gateway instance."""
        return self._llm_gateway
