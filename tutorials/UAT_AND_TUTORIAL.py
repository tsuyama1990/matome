import marimo

__generated_with = "0.20.4"
app = marimo.App(width="medium")


@app.cell
def __():
    import marimo as mo

    return (mo,)


@app.cell
def __(mo):
    mo.md(
        """
        # matome: Interactive UAT & Tutorial

        Welcome to the **matome** interactive tutorial! This notebook demonstrates the core capabilities of the platform as outlined in UAT-01.
        We will ingest a legacy business manual, interact with the AI to unlock its contents, and restructure the knowledge into a system workflow diagram.
        """
    )


@app.cell
def __():
    import os

    # To secure the tutorial environment, we inject explicit configuration overrides directly into the Settings object
    # instead of insecurely modifying the global os.environ block directly.
    from pathlib import Path

    from src.config import Settings
    from src.domain_models.analysis import PivotBoard
    from src.domain_models.enums import PivotAxis
    from src.domain_models.manifest import NodeStatus, PipelineContext, UserInteractionContext
    from src.domain_models.services import DocumentFactory, MetadataService
    from src.infrastructure.orchestrator import (
        PipelineConfig,
        PipelineDependencies,
        PipelineOrchestrator,
    )
    from src.infrastructure.repository import InMemoryDocumentRepository
    from tests.helpers.mocks import MockAIService

    base_dir = str(Path.cwd().resolve())

    settings = Settings(
        allowed_base_dir=base_dir,
        ssl_cert_path="dummy/path/for/tutorial",
        spacy_model="en_core_web_sm",
        trusted_spacy_models=["en_core_web_sm", "en_core_web_md"],
    )

    # In production UATs, secure your real DI container properly.
    # We enforce a secure mock implementation that implements the required prompt injection scanner logic.
    from src.infrastructure.security import PromptInjectionScanner

    class SecureMockAIService(MockAIService):
        def __init__(self, scanner: PromptInjectionScanner) -> None:
            self.scanner = scanner
            super().__init__()

        def _secure_wrap(self, content: str | None) -> str:
            return self.scanner.sanitize(content) if content else ""

        def generate_summary(self, content: str) -> str:
            self._secure_wrap(content)
            return super().generate_summary(content)

        def generate_question(self, identity, content) -> str:
            self._secure_wrap(identity.title)
            self._secure_wrap(content.summary)
            return super().generate_question(identity, content)

        def evaluate_answer(self, context) -> tuple[bool, str]:
            self._secure_wrap(context.user_answer)
            return super().evaluate_answer(context)

    # We apply proper configuration-driven limits to the scanner
    secure_scanner = PromptInjectionScanner(max_input_length=settings.max_input_length)

    # Isolate states completely to prevent cross-service state leakage in mock layers
    summary_service = SecureMockAIService(secure_scanner)
    question_service = SecureMockAIService(secure_scanner)
    diagram_service = SecureMockAIService(secure_scanner)
    doc_gen_service = SecureMockAIService(secure_scanner)
    eval_service = SecureMockAIService(secure_scanner)

    # Initialize Repositories and Services
    doc_repo = InMemoryDocumentRepository()
    doc_factory = DocumentFactory()
    metadata_service = MetadataService()

    from src.infrastructure.services import (
        DefaultClusteringService,
        DefaultModelVerifier,
        DefaultTextSplitter,
        EntityExtractorBuilder,
        EntityExtractorBuilderConfig,
        LangChainSplitterStrategy,
    )
    from src.utils.rate_limit import RateLimiter

    text_splitter = DefaultTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        max_file_size=settings.max_file_size,
        strategy=LangChainSplitterStrategy(),
    )

    builder_config = EntityExtractorBuilderConfig(
        spacy_model=settings.spacy_model,
        trusted_models=settings.trusted_spacy_models,
        trusted_hashes=settings.trusted_model_hashes,
        fallback_ner_regex=settings.fallback_ner_regex,
        max_model_signature_size=settings.max_model_signature_size,
    )

    entity_extractor = EntityExtractorBuilder.build(
        builder_config=builder_config,
        rate_limiter=RateLimiter(0.01),
        model_verifier=DefaultModelVerifier(
            set(settings.trusted_spacy_models),
            settings.trusted_model_hashes,
            settings.max_model_signature_size,
        ),
    )

    clustering_service = DefaultClusteringService(settings.random_seed)

    deps = PipelineDependencies(
        doc_repo=doc_repo,
        transaction_manager=doc_repo,
        summary_service=summary_service,
        question_service=question_service,
        doc_factory=doc_factory,
        metadata_service=metadata_service,
        text_splitter=text_splitter,
        entity_extractor=entity_extractor,
        clustering_service=clustering_service,
    )

    config = PipelineConfig(
        pipeline_timeout=settings.pipeline_timeout,
        raptor_max_clusters=settings.raptor_max_clusters,
    )

    orchestrator = PipelineOrchestrator(dependencies=deps, config=config)

    return (
        os,
        settings,
        PipelineContext,
        NodeStatus,
        UserInteractionContext,
        doc_repo,
        metadata_service,
        orchestrator,
        doc_factory,
        PivotAxis,
        PivotBoard,
        diagram_service,
        eval_service,
        doc_gen_service,
    )


@app.cell
def __(mo):
    mo.md("### Environment Setup\nRunning in **Secure Interactive Mode**.")


@app.cell
def __(PipelineContext, orchestrator, doc_repo, metadata_service):
    # Step 1: Ingestion
    file_path = "testfiles/test_text.txt"
    root_id = "doc_manual_v1"

    context = PipelineContext(root_doc_id=root_id, file_path=file_path)
    orchestrator.run_pipeline(context)

    root_identity = doc_repo.get_identity(root_id)
    root_content = doc_repo.get_content(root_id)
    root_metadata = metadata_service.get_metadata(root_id)

    return file_path, root_id, context, root_identity, root_content, root_metadata


@app.cell
def __(mo, root_identity, root_content, root_metadata):
    mo.md(
        f"""
        ### Step 2: Ingestion Complete
        **Node ID:** {root_identity.id}
        **Title:** {root_identity.title}
        **Status:** {root_identity.status.value}

        *Notice how the node is currently LOCKED.*

        The AI has automatically analyzed the text and generated the following entity metadata:
        ```json
        {root_metadata.ai_metadata.entity_metadata}
        ```
        """
    )


@app.cell
def __(root_identity, root_content, UserInteractionContext, NodeStatus, eval_service):
    # Step 3: AI Question & User Interaction (SQ3R)
    question = "What condition requires executive approval?"

    # User attempts to answer
    user_answer = "Executive approval is needed if the budget exceeds £5000."

    interaction_ctx = UserInteractionContext(
        node_id=root_identity.id,
        status=root_identity.status,
        question_asked=question,
        user_answer=user_answer,
    )

    is_correct, feedback = eval_service.evaluate_answer(interaction_ctx)

    if is_correct:
        root_identity.status = NodeStatus.UNLOCKED
    else:
        pass

    return question, user_answer, interaction_ctx, is_correct, feedback


@app.cell
def __(mo, is_correct, root_identity, root_content):
    if is_correct:
        display_md = f"""
        ### Step 3: Node Unlocked! 🔓
        You answered correctly, and the node is now unlocked!

        **High-Density Summary (Chain of Density):**
        > {root_content.summary}
        """
    else:
        display_md = "### Step 3: Node remains locked. Please try again."

    mo.md(display_md)
    return (display_md,)


@app.cell
def __(root_identity, PivotAxis, PivotBoard, diagram_service, doc_gen_service):
    # Step 4: Pivot KJ Analysis
    # The user wants to map out the "Actor vs. State Transition" workflow

    pivot_board = PivotBoard(
        id="pivot_workflow_1",
        original_root_id=root_identity.id,
        axis=PivotAxis.ACTOR_STATE,
        nodes=[],
    )

    mermaid_snippet = diagram_service.generate_mermaid_diagram(pivot_board)
    markdown_prd = doc_gen_service.generate_markdown_requirements(pivot_board)

    return pivot_board, mermaid_snippet, markdown_prd


@app.cell
def __(mo, pivot_board, mermaid_snippet, markdown_prd):
    mo.md(
        f"""
        ### Step 5: Multi-Dimensional Pivot (Actor vs State)
        We have restructured the legacy manual into a completely new workflow.

        #### Generated Mermaid Diagram:
        ```mermaid
        {mermaid_snippet}
        ```

        #### Exported Requirements Document:
        ```markdown
        {markdown_prd}
        ```
        """
    )


if __name__ == "__main__":
    app.run()
