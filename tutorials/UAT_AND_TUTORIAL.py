import marimo

__generated_with = "0.20.4"
app = marimo.App()

@app.cell
def __():
    import marimo as mo
    return (mo,)

@app.cell
def __(mo):
    mo.md(
        """
        # matome: User Acceptance Testing and Tutorial

        Welcome to the matome executable tutorial! This notebook demonstrates the entire system architecture, from basic configuration to advanced insight generation.

        ## Section 1: Introduction and Configuration (Cycle 01 & 02)

        This section initializes the `AppConfig` and the `DIContainer`, demonstrating how the system handles missing API keys and how "Mock Mode" is activated.
        """
    )
    return ()

@app.cell
def __():
    import os
    import uuid
    import asyncio
    from pydantic import ValidationError
    from src.domain_models.config import AppConfig, ModelRoutingRules
    from src.application.di_container import DIContainer
    from src.interfaces.llm_protocol import LLMProtocol
    from src.infrastructure.test_services import (
        FallbackEmbeddingService,
        FallbackReasoningLLMService,
        FallbackLLMService,
        FallbackVectorDB,
    )

    print("Running UAT-01-01: Secure Application Configuration and Startup")
    # To test validation behavior, we rely on the Mock environment variables logic, ensuring no secrets are exposed.
    original_api = os.environ.pop("OPENROUTER_API_KEY", None)
    original_tenant = os.environ.pop("TENANT_ID", None)

    try:
        # Expected to fail due to missing keys
        AppConfig() # type: ignore[call-arg]
        raise AssertionError("Expected ValidationError due to missing keys")
    except ValidationError:
        print("Success: AppConfig correctly rejected missing configuration secrets.")

    return AppConfig, ModelRoutingRules, DIContainer, LLMProtocol, FallbackEmbeddingService, FallbackReasoningLLMService, FallbackLLMService, FallbackVectorDB, os, uuid, asyncio, original_api, original_tenant

@app.cell
def __(AppConfig, original_api, original_tenant, os):
    # Test valid key formatting with placeholder mock string to prevent leaking actual credentials.
    os.environ["OPENROUTER_API_KEY"] = (
        "sk-or-v1-mockmockmockmockmockmockmockmockmockmockmockmockmockmockmockmock"
    )
    os.environ["TENANT_ID"] = "test-tenant"

    config = AppConfig(
        openrouter_api_key="sk-or-v1-mockmockmockmockmockmockmockmockmockmockmockmockmockmockmockmock",  # type: ignore[arg-type]
        tenant_id="test-tenant",
    )

    # Asserting that the mock placeholder key doesn't leak into string representations.
    assert "mockmockmock" not in str(
        config
    ), "SecretStr leaked in string representation!"
    assert "**********" in str(config), "SecretStr did not mask correctly!"
    print("Success: SecretStr securely masked test key representations.")

    # Restore actual environment state so downstream cells behavior safely.
    if original_api:
        os.environ["OPENROUTER_API_KEY"] = original_api
    if original_tenant:
        os.environ["TENANT_ID"] = original_tenant

    return config,

@app.cell
def __(DIContainer, LLMProtocol, FallbackLLMService):
    print("Running UAT-01-02: Dependency Injection and Protocol Resolution")

    container = DIContainer()

    # We use FallbackLLMService, which correctly implements the LLMProtocol instead of an empty mock pass class.
    instance = FallbackLLMService()
    container.register_singleton(LLMProtocol, instance) # type: ignore[type-abstract]
    resolved = container.resolve(LLMProtocol)  # type: ignore[type-abstract]
    assert resolved is instance  # type: ignore[comparison-overlap]
    print("Success: Resolved singleton successfully via Dependency Injection.")

    return container, instance, resolved

@app.cell
def __(DIContainer, LLMProtocol, FallbackLLMService, os):
    print("Running UAT-01-03: Hybrid Environment Fallback Mode Execution")

    # We utilize FallbackLLMService from infrastructure directly as a complete mock implemention
    fallback_container = DIContainer()

    # Fallback to mock behaviors seamlessly.
    if os.environ.get("MATOME_MOCK_MODE", "true").lower() == "true":
        fallback_container.register_singleton(LLMProtocol, FallbackLLMService())  # type: ignore[type-abstract]

    assert isinstance(fallback_container.resolve(LLMProtocol), FallbackLLMService)  # type: ignore[type-abstract]
    print("Success: Fallback Mode Execution successfully resolved to robust fallback implementation.")

    return fallback_container,

@app.cell
def __(mo):
    mo.md(
        """
        ## Section 2: Document Ingestion and Chunking (Cycle 03)

        This section explains the "Lost-in-the-Middle" problem and how semantic chunking solves it. We invoke the `IngestionPipeline` to process raw document text logically, preparing structured chunks with generated vector embeddings.
        """
    )
    return ()

@app.cell
def __(FallbackLLMService, FallbackEmbeddingService, FallbackVectorDB, uuid, asyncio):
    from src.application.ingestion import IngestionPipeline
    from src.domain_models.document import SemanticChunk

    async def run_uat_02():
        print("Running UAT-02: Document Ingestion and Semantic Chunking")

        fallback_llm = FallbackLLMService()
        fallback_embed = FallbackEmbeddingService(dimension=384)
        fallback_db = FallbackVectorDB()

        pipeline = IngestionPipeline(llm=fallback_llm, embedding=fallback_embed, vector_db=fallback_db)
        pipeline._nlp = None  # type: ignore[assignment]

        sample_text = "This is the first sentence. This is the second sentence."

        chunks = await pipeline.process_text(sample_text)

        assert len(chunks) > 0
        for chunk in chunks:
            assert isinstance(chunk, SemanticChunk)
            assert isinstance(chunk.id, uuid.UUID)
            assert len(chunk.embedding) == 384
            assert chunk.content in sample_text

        print(f"Success: Text correctly chunked into {len(chunks)} SemanticChunks with valid dimensional embeddings.")
        return pipeline, chunks

    pipeline, chunks = asyncio.run(run_uat_02())
    return pipeline, chunks, IngestionPipeline, SemanticChunk

@app.cell
def __(mo):
    mo.md(
        """
        ## Section 3: RAPTOR Tree Generation (Cycle 04)

        This section demonstrates combating cognitive overload by building a hierarchical summary tree. We take the chunks from Section 2 and build an `EnrichedDocument` with structured recursive `RaptorNodes`.
        """
    )
    return ()

@app.cell
def __(chunks, uuid, FallbackReasoningLLMService, asyncio):
    from src.application.raptor_engine import RaptorEngine
    from src.infrastructure.test_services import FallbackClusteringService
    from src.domain_models.document import EnrichedDocument

    async def run_uat_03(chunks):
        print("Running UAT-03: RAPTOR Tree Generation")

        fallback_llm = FallbackReasoningLLMService(response_json='{"summary": "A mock summary of the clustered chunks.", "questions": ["What is this?"]}')
        fallback_clusterer = FallbackClusteringService()

        engine = RaptorEngine(llm=fallback_llm, clusterer=fallback_clusterer)

        doc_id = uuid.uuid4()
        doc = await engine.build_tree(document_id=doc_id, chunks=chunks)

        assert isinstance(doc, EnrichedDocument)
        assert doc.document_id == doc_id
        assert len(doc.raptor_nodes) > 0

        print(f"Success: Built RAPTOR tree with {len(doc.raptor_nodes)} multi-layer nodes.")
        return doc

    doc = asyncio.run(run_uat_03(chunks))
    return doc, RaptorEngine, FallbackClusteringService, EnrichedDocument

@app.cell
def __(mo):
    mo.md(
        """
        ## Section 4: Interactive Learning (SQ3R) (Cycle 05)

        This section showcases the gamified learning loop (Survey, Question, Read, Recite, Review). It simulates dynamically querying contexts to lock and unlock user nodes dynamically depending on validation metrics.
        """
    )
    return ()

@app.cell
def __(doc, FallbackReasoningLLMService, asyncio):
    from src.application.sq3r_service import SQ3REngine
    from src.domain_models.graph_state import LearningProgress

    async def run_uat_04(doc):
        print("Running UAT-04: Interactive Learning (SQ3R)")

        fallback_llm = FallbackReasoningLLMService(response_json='{"is_correct": true, "feedback": "Good job."}')
        engine = SQ3REngine(llm=fallback_llm)

        target_node = doc.raptor_nodes[0]

        question = await engine.generate_unlock_question(target_node)
        assert isinstance(question, str)
        print("Generated Question:", question)

        progress = LearningProgress(user_id="test_user", document_id=doc.document_id)
        assert target_node.id not in progress.unlocked_node_ids

        result = await engine.evaluate_answer(target_node, "My user answer")
        assert result.is_correct is True

        if result.is_correct:
            progress.unlocked_node_ids.add(target_node.id)

        assert target_node.id in progress.unlocked_node_ids
        print("Success: Evaluated answer and correctly unlocked node based on valid assessment progress.")
        return progress

    progress = asyncio.run(run_uat_04(doc))
    return progress, SQ3REngine, LearningProgress

@app.cell
def __(mo):
    mo.md(
        """
        ## Section 5: Advanced Insights (Pivot KJ) (Cycle 06)

        The grand finale: demonstrating the transition from reading to creating by reconstructing the knowledge graph along new target multidimensional axes utilizing semantic vectors and extracting generated insightful Markdown reports.
        """
    )
    return ()

@app.cell
def __(uuid, SemanticChunk, FallbackVectorDB, FallbackReasoningLLMService, FallbackEmbeddingService, EnrichedDocument, asyncio):
    from src.application.pivot_workflow import PivotEngine, ExportService
    from src.domain_models.document import ChunkMetadata

    async def run_uat_05():
        print("Running UAT-05: Multi-Dimensional Knowledge Reconstruction (Pivot)")
        fallback_db = FallbackVectorDB()
        chunk_id = uuid.uuid4()
        chunk = SemanticChunk(
            id=chunk_id,
            content="User admin manages settings.",
            embedding=[0.1] * 384,
            metadata=ChunkMetadata(source_file="test.txt", actor_axis="Admin User"),
        )
        await fallback_db.upsert([chunk])

        json_resp = f'{{"nodes": [{{"label": "Admin User", "summary": "Manages system settings.", "source_chunk_ids": ["{chunk_id!s}"]}}]}}'
        fallback_llm = FallbackReasoningLLMService(response_json=json_resp)
        fallback_embed = FallbackEmbeddingService(dimension=384)

        engine = PivotEngine(
            llm=fallback_llm,
            vector_db=fallback_db,
            embedding=fallback_embed,
            allowed_axes=frozenset({"system actors"}),
        )
        doc_id = uuid.uuid4()
        doc = EnrichedDocument(document_id=doc_id, original_text="...", chunks=[chunk], raptor_nodes=[])

        state = await engine.execute_pivot(doc, "System Actors")

        assert state is not None
        assert state.axis_name == "System Actors"
        assert len(state.nodes) == 1
        assert state.nodes[0].label == "Admin User"
        print("Success: PivotState generated multidimensional data successfully from VectorDB semantic matching.")

        print("Running UAT-05-02: Artifact Export Generation (Markdown)")
        export_service = ExportService()
        markdown_output = export_service.generate_markdown(state)
        assert "# System Actors" in markdown_output
        assert "## Admin User" in markdown_output
        print("Success: Analytical MD Document successfully generated correctly via mapped insights structure.")
        return state, markdown_output

    state, markdown_output = asyncio.run(run_uat_05())
    return state, markdown_output, PivotEngine, ExportService, ChunkMetadata

