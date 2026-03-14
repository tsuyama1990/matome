"""
End-to-End tests mapping to the entire user journey.
"""

import uuid

import pytest

from src.application import PivotKJEngine, RAPTOREngine, SQ3REngine
from src.domain_models import ChunkMetadata, SemanticChunk
from src.infrastructure.clustering import UMAPGMMClusteringStrategy
from src.infrastructure.test_services import SimpleParsingService


class MockE2ELLM:
    """Mock LLM for E2E tests."""

    async def generate(self, prompt: str) -> str:
        if "feedback" in prompt.lower():
            return "Good job. Correct."
        if "question" in prompt.lower():
            return "What is the core condition?"
        if "summarize" in prompt.lower():
            return "Executive approval is strictly needed if the budget exceeds 5000."

        raise ValueError("Unexpected prompt without context: " + prompt)


@pytest.mark.asyncio
async def test_uat_01_quick_start() -> None:
    """Simulates UAT-01: Quick Start for a Product Manager."""

    # 1. Ingestion (Survey)
    parser = SimpleParsingService()
    text = "The system defines standard workflows. Executive approval is strictly needed if the budget exceeds 5000. Normal flows skip this."
    raw_chunks = parser.parse_document(text)

    chunks = []
    for i, content in enumerate(raw_chunks):
        chunks.append(
            SemanticChunk(
                id=uuid.uuid4(),
                content=content,
                embedding=[float(i) / 10.0] * 768,
                metadata=ChunkMetadata(
                    source_file="testfiles/test_text.txt",
                    actor_axis="Executive" if "Executive" in content else "System",
                ),
            )
        )

    llm = MockE2ELLM()
    raptor = RAPTOREngine(
        llm=llm, clustering_strategy=UMAPGMMClusteringStrategy(), max_levels=2, max_clusters=2
    )

    nodes = await raptor.cluster_chunks(chunks)
    assert len(nodes) > 0

    # 2. Interaction (Question & Read)
    sq3r = SQ3REngine(llm=llm)
    target_node = nodes[0]

    question = await sq3r.generate_question(target_node)
    assert "what is" in question.lower()

    # 3. Active Recall (Recite)
    feedback = await sq3r.evaluate_answer("I think it is 5000.", target_node)
    assert "Good job" in feedback

    # 4. Transformation (Pivot KJ)
    pivot_engine = PivotKJEngine(allowed_axes=frozenset({"actor", "time", "entities"}))
    clusters = pivot_engine.pivot(chunks, axis="actor")

    assert "Executive" in clusters
    assert len(clusters["Executive"]) == 1
    assert (
        clusters["Executive"][0].content
        == "Executive approval is strictly needed if the budget exceeds 5000."
    )
    assert "System" in clusters
