import marimo

__generated_with = "0.8.2"
app = marimo.App(width="medium")


@app.cell
def __():
    import marimo as mo

    from src.application.ai import DefaultAIService
    from src.config import Settings
    from src.domain_models import (
        DocumentFactory,
        NodeStatus,
        PipelineContext,
        PivotAxis,
        PivotBoard,
        PivotBoardViewNode,
        UserInteractionContext,
    )
    from src.infrastructure import InMemoryDocumentRepository, PipelineOrchestrator
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
        mo,
    )


@app.cell
def __(
    DefaultAIService,
    DocumentFactory,
    InMemoryDocumentRepository,
    MockAIService,
    PipelineOrchestrator,
    Settings,
    mo,
):
    mo.md("# matome: Frictionless Active Learning Tutorial")

    settings = Settings()
    repo = InMemoryDocumentRepository()

    # Conditional AI service initialization based on environment config
    api_key = settings.openrouter_api_key if settings.openrouter_api_key else None

    if api_key:
        ai = DefaultAIService(api_key=api_key, model=settings.text_fast_model)
        mode_text = "Real AI Integration Mode (OpenRouter active)."
    else:
        ai = MockAIService()
        mode_text = "Mock Mode (No OpenRouter key found. Running with mock AI logic)."

    factory = DocumentFactory()
    orchestrator = PipelineOrchestrator(doc_repo=repo, ai_service=ai, doc_factory=factory)

    mo.md(f"System initialized successfully in: **{mode_text}**")
    return ai, factory, orchestrator, repo, settings


@app.cell
def __(PipelineContext, orchestrator, repo, settings, mo):
    mo.md("## Step 1: Ingestion")
    content = "This is a dummy legacy business manual. Rule 1: Executive approval is needed if the budget > 5000."
    context = PipelineContext(root_doc_id=settings.default_root_doc_id, content=content)
    orchestrator.run_pipeline(context)

    root_node = repo.get_node(settings.default_root_doc_id)
    mo.md(f"Document Ingested! Root Node Title: **{root_node.title}**")
    return content, context, root_node


@app.cell
def __(ai, root_node, mo):
    mo.md("## Step 2: Interaction (SQ3R)")
    question = ai.generate_question(root_node)
    mo.md(f"**AI Tutor asks:** {question}")
    return (question,)


@app.cell
def __(NodeStatus, UserInteractionContext, ai, root_node, mo):
    mo.md("### User attempts to answer")
    user_answer = "Executive approval is needed if budget > 5000."
    interaction = UserInteractionContext(
        node_id=root_node.id,
        status=root_node.status,
        question_asked="What is the key point of Business Manual?",
        user_answer=user_answer,
    )

    success, feedback = ai.evaluate_answer(interaction)

    if success:
        root_node.status = NodeStatus.UNLOCKED
        result_md = f"**Result:** {feedback} Node Unlocked! Summary: {root_node.content.summary}"
    else:
        result_md = f"**Result:** {feedback} Try again."

    mo.md(result_md)
    return feedback, interaction, result_md, success, user_answer


@app.cell
def __(PivotAxis, PivotBoard, PivotBoardViewNode, ai, root_node, mo):
    mo.md("## Step 3: Pivot KJ Analysis")

    board = PivotBoard(
        id="board_1",
        original_root_id=root_node.id,
        axis=PivotAxis.ACTOR_STATE,
        nodes=[
            PivotBoardViewNode(
                node_id=root_node.id, x_position=0.1, y_position=0.2, cluster_id="cluster_1"
            )
        ],
    )

    mermaid_code = ai.generate_mermaid_diagram(board)

    mo.md(f"**Generated Mermaid Diagram:**\n```mermaid\n{mermaid_code}\n```")
    return board, mermaid_code


if __name__ == "__main__":
    app.run()
