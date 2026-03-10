import marimo

__generated_with = "0.8.2"
app = marimo.App(width="medium")


@app.cell
def __():
    import os

    import marimo as mo
    from pydantic import ValidationError

    from src.application.ai import DefaultAIService
    from src.config import EnvCredentialProvider, Settings
    from src.domain_models import (
        DocumentFactory,
        NodeStatus,
        PipelineContext,
        PivotAxis,
        PivotBoard,
        PivotBoardViewNode,
        UserInteractionContext,
    )
    from src.domain_models.services import MetadataService
    from src.infrastructure import InMemoryDocumentRepository, PipelineOrchestrator
    from src.infrastructure.orchestrator import PipelineConfig, PipelineDependencies
    from src.infrastructure.services import (
        DefaultClusteringService,
        DefaultTextSplitter,
        EntityExtractorBuilder,
        LangChainSplitterStrategy,
        RequestsHTTPClient,
        TenacityRetryPolicy,
    )
    from tests.helpers.mocks import MockAIService

    return (
        DefaultAIService,
        DocumentFactory,
        InMemoryDocumentRepository,
        MockAIService,
        NodeStatus,
        PipelineContext,
        PipelineOrchestrator,
        PivotAxis,
        PivotBoard,
        PivotBoardViewNode,
        Settings,
        UserInteractionContext,
        EnvCredentialProvider,
        PipelineDependencies,
        PipelineConfig,
        RequestsHTTPClient,
        TenacityRetryPolicy,
        DefaultTextSplitter,
        LangChainSplitterStrategy,
        EntityExtractorBuilder,
        DefaultClusteringService,
        MetadataService,
        ValidationError,
        mo,
        os,
    )


@app.cell
def __(
    DefaultAIService,
    DocumentFactory,
    InMemoryDocumentRepository,
    MockAIService,
    PipelineOrchestrator,
    Settings,
    EnvCredentialProvider,
    PipelineDependencies,
    PipelineConfig,
    RequestsHTTPClient,
    TenacityRetryPolicy,
    DefaultTextSplitter,
    LangChainSplitterStrategy,
    EntityExtractorBuilder,
    DefaultClusteringService,
    MetadataService,
    ValidationError,
    mo,
    os,
):
    mo.md("# matome: Frictionless Active Learning Tutorial")

    # Mock environment configuration for tutorial purposes
    tutorial_env = {
        "OPENROUTER_API_URL": "https://openrouter.ai/api/v1/chat/completions",
        "TEXT_FAST_MODEL": "google/gemini-2.5-flash",
        "TEXT_REASONING_MODEL": "deepseek/deepseek-reasoner",
        "MULTIMODAL_MODEL": "openai/gpt-4o",
        "ALLOWED_BASE_DIR": os.environ.get("ALLOWED_BASE_DIR", str(os.path.abspath(os.getcwd()))),
    }
    for k, v in tutorial_env.items():
        if k not in os.environ:
            os.environ[k] = v

    try:
        settings = Settings()
        api_key = (
            settings.credentials.openrouter_api_key.get_secret_value()
            if settings.credentials.openrouter_api_key
            else None
        )
        has_real_key = bool(api_key and not api_key.startswith("sk-or-v1-mock-key"))
    except ValidationError:
        # Provide safe mock default dynamically through environment overriding without hardcoding a dummy key
        tutorial_env["OPENROUTER_API_KEY"] = os.environ.get("OPENROUTER_API_KEY", "sk-or-v1-mock-key-1234")
        for k, v in tutorial_env.items():
            os.environ[k] = v
        settings = Settings()
        api_key = None
        has_real_key = False

    repo = InMemoryDocumentRepository()

    if has_real_key and api_key:
        provider = EnvCredentialProvider(settings.credentials)
        http_client = RequestsHTTPClient()
        retry_policy = TenacityRetryPolicy()
        ai = DefaultAIService(
            credential_provider=provider,
            api_url=settings.openrouter_api_url,
            text_fast_model=settings.text_fast_model,
            text_reasoning_model=settings.text_reasoning_model,
            ai_timeout=settings.ai_timeout,
            http_client=http_client,
            retry_policy=retry_policy,
        )
        mode_text = "Real AI Integration Mode (OpenRouter active)."
    else:
        ai = MockAIService()
        mode_text = "Mock Mode (No OpenRouter key found. Running with mock AI logic)."

    factory = DocumentFactory()
    metadata_service = MetadataService()

    text_splitter = DefaultTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        max_file_size=settings.max_file_size,
        strategy=LangChainSplitterStrategy(),
    )
    entity_extractor = EntityExtractorBuilder.build(
        spacy_model=settings.spacy_model,
        trusted_models=settings.trusted_spacy_models,
        trusted_hashes=settings.trusted_model_hashes,
        fallback_ner_regex=settings.fallback_ner_regex,
        max_model_signature_size=settings.max_model_signature_size,
    )
    clustering_service = DefaultClusteringService(settings.random_seed)

    deps = PipelineDependencies(
        doc_repo=repo,
        transaction_manager=repo,
        summary_service=ai,
        question_service=ai,
        doc_factory=factory,
        metadata_service=metadata_service,
        text_splitter=text_splitter,
        entity_extractor=entity_extractor,
        clustering_service=clustering_service,
    )
    config = PipelineConfig(
        pipeline_timeout=settings.pipeline_timeout, raptor_max_clusters=settings.raptor_max_clusters
    )

    orchestrator = PipelineOrchestrator(dependencies=deps, config=config)

    mo.md(f"System initialized successfully in: **{mode_text}**")
    return ai, factory, orchestrator, repo, settings


@app.cell
def __(PipelineContext, orchestrator, repo, settings, mo):
    mo.md("## Step 1: Ingestion")
    content = "This is a dummy legacy business manual. Rule 1: Executive approval is needed if the budget > 5000."
    context = PipelineContext(root_doc_id=settings.default_root_doc_id, content=content)
    orchestrator.run_pipeline(context)

    identity_node = repo.get_identity(settings.default_root_doc_id)
    content_node = repo.get_content(settings.default_root_doc_id)
    mo.md(f"Document Ingested! Root Node Title: **{identity_node.title}**")
    return content, context, identity_node, content_node


@app.cell
def __(ai, identity_node, content_node, mo):
    mo.md("## Step 2: Interaction (SQ3R)")
    question = ai.generate_question(identity_node, content_node)
    mo.md(f"**AI Tutor asks:** {question}")
    return (question,)


@app.cell
def __(NodeStatus, UserInteractionContext, ai, identity_node, content_node, mo):
    mo.md("### User attempts to answer")
    user_answer = "Executive approval is needed if budget > 5000."
    interaction = UserInteractionContext(
        node_id=identity_node.id,
        status=identity_node.status,
        question_asked="What is the key point of Business Manual?",
        user_answer=user_answer,
    )

    success, feedback = ai.evaluate_answer(interaction)

    if success:
        identity_node.status = NodeStatus.UNLOCKED
        result_md = f"**Result:** {feedback} Node Unlocked! Summary: {content_node.summary}"
    else:
        result_md = f"**Result:** {feedback} Try again."

    mo.md(result_md)
    return feedback, interaction, result_md, success, user_answer


@app.cell
def __(PivotAxis, PivotBoard, PivotBoardViewNode, ai, identity_node, mo):
    mo.md("## Step 3: Pivot KJ Analysis")

    board = PivotBoard(
        id="board_1",
        original_root_id=identity_node.id,
        axis=PivotAxis.ACTOR_STATE,
        nodes=[
            PivotBoardViewNode(
                node_id=identity_node.id, x_position=0.1, y_position=0.2, cluster_id="cluster_1"
            )
        ],
    )

    mermaid_code = ai.generate_mermaid_diagram(board)

    mo.md(f"**Generated Mermaid Diagram:**\n```mermaid\n{mermaid_code}\n```")
    return board, mermaid_code


if __name__ == "__main__":
    app.run()
