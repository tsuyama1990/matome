import marimo

__generated_with = "0.20.4"
app = marimo.App(width="medium")

@app.cell
def _setup():
    import os
    import sys
    from pathlib import Path

    # Ensure src is in pythonpath
    sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

    import marimo as mo
    import uuid as _uuid

    # Configure mock vs real mode
    api_key = os.environ.get("OPENROUTER_API_KEY")
    is_mock_mode = not api_key

    if is_mock_mode:
        mo.md("# matome UAT & Tutorial\n\n**Mode:** Mock (No `OPENROUTER_API_KEY` detected. Using safe, deterministic test implementations.)")
    else:
        mo.md("# matome UAT & Tutorial\n\n**Mode:** Real (Executing against external LLM providers.)")

    return Path, _uuid, is_mock_mode, mo, os, sys


@app.cell
def _init_system(is_mock_mode, mo, os):
    from src.application import PivotKJEngine, SQ3REngine
    from src.config.settings import AppConfig, ModelConfig
    from src.domain_models import ChunkMetadata, RaptorNode, SemanticChunk
    from src.interfaces.dependencies import DIContainer, LLMProtocol

    # Initialize configs directly using test/mock paths if needed, but since we use pydantic-settings
    # it expects env vars. We will set dummy env vars for initialization if missing.
    if is_mock_mode:
        os.environ["DATABASE_URI_ENCRYPTED"] = "sqlite:///test.db"
        os.environ["OPENROUTER_API_URL"] = "https://example.com/api"
        os.environ["TEXT_FAST_MODEL"] = "test-fast"
        os.environ["TEXT_REASONING_MODEL"] = "test-reasoning"
        os.environ["MULTIMODAL_MODEL"] = "test-multimodal"
        os.environ["ALLOWED_HOSTS"] = "[\"example.com\"]"

    container = DIContainer()

    # We construct AppConfig
    app_config = AppConfig(
        upload_dir="testfiles",
        max_file_size=50 * 1024 * 1024,
    )
    container.register(AppConfig, lambda: app_config)

    # In Mock Mode we register dummy LLM, otherwise the real one
    if is_mock_mode:
        from src.infrastructure.test_services import SafeTestLLMService
        test_llm = SafeTestLLMService()
        container.register(LLMProtocol, lambda: test_llm)
    else:
        from src.infrastructure.llm_gateway import OpenRouterClient
        model_config = ModelConfig()
        container.register(ModelConfig, lambda: model_config)

        def llm_factory() -> LLMProtocol:
            mc = container.resolve(ModelConfig)
            return OpenRouterClient(
                api_url=str(mc.openrouter_api_url),
                api_key=os.environ["OPENROUTER_API_KEY"],
                model=mc.text_fast_model,
                timeout=mc.llm_timeout
            )
        container.register(LLMProtocol, llm_factory)

    # Setup core services manually to simulate the workflow for tutorial
    llm = container.resolve(LLMProtocol)
    sq3r_engine = SQ3REngine(llm=llm)
    pivot_engine = PivotKJEngine(allowed_axes=frozenset(app_config.pivot_allowed_axes))

    mo.md("## Step 1: Initialization Complete\nDI Container and configurations are set up.")
    return (
        AppConfig,
        ChunkMetadata,
        DIContainer,
        LLMProtocol,
        PivotKJEngine,
        RaptorNode,
        SQ3REngine,
        SemanticChunk,
        app_config,
        container,
        llm,
        pivot_engine,
        sq3r_engine,
    )


@app.cell
def _ingestion_simulation(ChunkMetadata, Path, SemanticChunk, _uuid, mo):
    mo.md("## Step 2 & 3: Ingestion & RAPTOR Tree Simulation\n\nSimulating file chunking and NLP tagging.")

    test_file_path = Path("testfiles/test_text.txt")
    if not test_file_path.exists():
        # Fallback if file isn't present
        raw_content = "This is a test document. It contains information about actors, systems, and states. The system processes data rapidly."
    else:
        with test_file_path.open("r", encoding="utf-8") as f:
            raw_content = f.read(500) # Read snippet

    # Simulating the SemanticChunkingService and NLP tagging to avoid complex ML imports in tutorial
    chunks = [
        SemanticChunk(
            id=_uuid.uuid4(),
            content="A Product Manager needs executive approval for budgets over £5000.",
            embedding=[0.1] * 256,
            metadata=ChunkMetadata(
                source_file="test_text.txt",
                extracted_entities=["Executive", "Product Manager"],
                actor_axis="Product Manager",
                time_axis="Present"
            )
        ),
        SemanticChunk(
            id=_uuid.uuid4(),
            content="The system actor must transition the state to 'Pending'.",
            embedding=[0.2] * 256,
            metadata=ChunkMetadata(
                source_file="test_text.txt",
                extracted_entities=["System Actor"],
                actor_axis="System Actor",
                time_axis="Future"
            )
        )
    ]

    mo.md(f"Created {len(chunks)} chunks from ingested text. Printing first chunk content: \n\n> {chunks[0].content}")
    return chunks, raw_content, test_file_path


@app.cell
def _interactive_sq3r(RaptorNode, _uuid, mo, sq3r_engine):
    import asyncio as _asyncio

    mo.md("## Step 4: Interactive SQ3R Loop\n\nWe unlock a node by answering a question.")

    node = RaptorNode(
        node_id=str(_uuid.uuid4()),
        level=1,
        children_ids=[],
        summarized_content="Executive approval is strictly needed if the total requested budget exceeds £5000.",
        is_unlocked=False
    )

    async def run_sq3r():
        # Generate Question
        question = await sq3r_engine.generate_question(node)

        # Simulating User Answer (Correct)
        user_answer = "high budget over 5000"
        feedback = await sq3r_engine.evaluate_answer(user_answer, node)
        node.is_unlocked = True
        return question, feedback

    question, feedback = _asyncio.run(run_sq3r())

    mo.md(f"**AI Question:** {question}\n\n**Sandwich Feedback:** {feedback}\n\n**Node Unlocked:** {node.is_unlocked}")
    return feedback, node, question, run_sq3r


@app.cell
def _pivot_analysis(chunks, mo, pivot_engine):
    mo.md("## Step 5: Pivot Analysis (MD-SKJ)\n\nRe-clustering chunks based on 'actor' axis.")

    # Pivot chunks along the Actor axis
    clusters = pivot_engine.pivot(chunks, "actor")

    cluster_output = ""
    for cluster_name, cluster_chunks in clusters.items():
        cluster_output += f"\n- **Cluster:** {cluster_name}\n"
        for c in cluster_chunks:
            cluster_output += f"  - {c.content}\n"

    mo.md(cluster_output)
    return cluster_output, clusters


@app.cell
def _export_demo(clusters, llm, mo):
    import asyncio as _asyncio

    mo.md("## Step 6: Export Demonstration\n\nGenerating Markdown and Mermaid.js sequence diagrams.")

    async def generate_exports():
        cluster_text = ""
        for cluster_name, chunk_list in clusters.items():
            cluster_text += f"\\n## Cluster: {cluster_name}\\n"
            for c in chunk_list:
                cluster_text += f"- {c.content}\\n"

        markdown_prompt = (
            "You are a system architect. Based on the following clustered requirements, "
            "generate a formal Markdown requirements document (PRD format). "
            f"Clusters:\\n{cluster_text}"
        )

        mermaid_prompt = (
            "You are a system architect. Based on the following clustered requirements, "
            "generate a valid Mermaid.js sequence diagram (only output the ```mermaid block). "
            f"Clusters:\\n{cluster_text}"
        )

        md_doc = await llm.generate(markdown_prompt)
        mermaid_doc = await llm.generate(mermaid_prompt)
        return md_doc, mermaid_doc

    md_doc, mermaid_doc = _asyncio.run(generate_exports())

    mo.md(f"### Generated PRD Markdown\n\n{md_doc}\n\n### Generated Mermaid Diagram\n\n{mermaid_doc}")
    return generate_exports, md_doc, mermaid_doc


if __name__ == "__main__":
    app.run()
