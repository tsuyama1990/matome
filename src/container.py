import importlib
from collections.abc import Callable
from typing import Any

from src.domain_models import PipelineConfig
from src.interfaces import (
    ActiveLearningService,
    DocumentProcessingService,
    KnowledgeGraphService,
    LLMProtocol,
)


def resolve_class(import_path: str) -> Callable[..., Any]:
    """Dynamically resolves a class from a string path (e.g., 'src.module.ClassName')."""
    module_path, class_name = import_path.rsplit(".", 1)
    try:
        module = importlib.import_module(module_path)
    except Exception as e:
        msg = f"Failed to dynamically import module {module_path}: {e}"
        raise ImportError(msg) from e

    cls = getattr(module, class_name)
    if not callable(cls):
        msg = f"Resolved object {class_name} is not callable."
        raise TypeError(msg)

    return cls  # type: ignore[no-any-return]


class ProductionDIContainer:
    """Dependency Injection container that automatically resolves and initializes components via factories registry."""

    def __init__(
        self,
        llm_gateway_factory: Callable[[], LLMProtocol],
        document_processor_factory: Callable[[], DocumentProcessingService],
        knowledge_graph_factory: Callable[[], KnowledgeGraphService],
        active_learning_factory: Callable[[], ActiveLearningService],
        config: PipelineConfig | None = None,
    ) -> None:
        self._config = config or PipelineConfig()

        self._llm_factory = llm_gateway_factory
        self._document_factory = document_processor_factory
        self._knowledge_graph_factory = knowledge_graph_factory
        self._active_learning_factory = active_learning_factory

        if not callable(self._llm_factory):
            msg = "llm_gateway_factory must be a callable factory function."
            raise TypeError(msg)
        if not callable(self._document_factory):
            msg = "document_processor_factory must be a callable factory function."
            raise TypeError(msg)
        if not callable(self._knowledge_graph_factory):
            msg = "knowledge_graph_factory must be a callable factory function."
            raise TypeError(msg)
        if not callable(self._active_learning_factory):
            msg = "active_learning_factory must be a callable factory function."
            raise TypeError(msg)

        # Initialize components dynamically strictly from factories
        self._llm_gateway = self._llm_factory()
        self._document_processor = self._document_factory()
        self._knowledge_graph = self._knowledge_graph_factory()
        self._active_learning = self._active_learning_factory()

    @staticmethod
    def _build_llm_factory(config: PipelineConfig) -> Callable[[], LLMProtocol]:
        def factory() -> LLMProtocol:
            cls = resolve_class(config.llm_service_path)
            # Support both architectures: with and without middleware routing dependencies
            from src.infrastructure.openrouter import OpenRouterGateway

            if config.llm_service_path == "src.infrastructure.llm_middleware.LLMMiddlewareService":
                gateway = OpenRouterGateway(config.credentials, config)
                return cls(gateway, config)  # type: ignore
            # Handle standard instantiation
            return cls(config.credentials, config)  # type: ignore

        return factory

    @staticmethod
    def _build_document_factory(config: PipelineConfig) -> Callable[[], DocumentProcessingService]:
        def factory() -> DocumentProcessingService:
            cls = resolve_class(config.document_service_path)
            return cls()  # type: ignore

        return factory

    @staticmethod
    def _build_knowledge_graph_factory(
        config: PipelineConfig,
    ) -> Callable[[], KnowledgeGraphService]:
        def factory() -> KnowledgeGraphService:
            cls = resolve_class(config.graph_service_path)
            return cls()  # type: ignore

        return factory

    @staticmethod
    def _build_active_learning_factory(
        config: PipelineConfig,
    ) -> Callable[[], ActiveLearningService]:
        def factory() -> ActiveLearningService:
            cls = resolve_class(config.active_learning_service_path)
            return cls()  # type: ignore

        return factory

    @property
    def config(self) -> PipelineConfig:
        return self._config

    @property
    def llm_gateway(self) -> LLMProtocol:
        return self._llm_gateway

    @property
    def document_processor(self) -> DocumentProcessingService:
        return self._document_processor

    @property
    def knowledge_graph(self) -> KnowledgeGraphService:
        return self._knowledge_graph

    @property
    def active_learning(self) -> ActiveLearningService:
        return self._active_learning
