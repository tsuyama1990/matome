"""
End-to-End tests mapping to the entire user journey.
"""

import uuid

import pytest
from pydantic import ValidationError

from src.application import IngestionPipeline, PivotKJEngine, RaptorEngine, SQ3REngine
from src.domain_models import ChunkMetadata, SemanticChunk
from src.infrastructure.clustering import UMAPGMMClusteringStrategy
from src.infrastructure.test_services import (
    DummyEmbeddingService,
    PlainTextParser,
    SafeTestLLMService,
    SimpleParsingService,
)


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

    async def generate_text(self, prompt: str, model: str) -> str:
        return await self.generate(prompt)


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
    raptor = RaptorEngine(llm=llm, clustering_strategy=UMAPGMMClusteringStrategy(), max_clusters=2)

    nodes = await raptor.build_tree(chunks)
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


class DummyE2ELLMService(SafeTestLLMService):
    """Specific dummy LLM returning a valid JSON string for ingestion tests."""

    async def generate(self, prompt: str) -> str:
        self._call_count += 1
        return '{"entities": ["MockEntityA"], "time_axis": "Present"}'

    async def generate_text(self, prompt: str, model: str) -> str:
        self._call_count += 1
        return '{"entities": ["MockEntityA"], "time_axis": "Present"}'


@pytest.mark.asyncio
async def test_uat_03_01_end_to_end_ingestion() -> None:
    """UAT-03-01: End-to-End Document Ingestion (Mock Mode)"""
    llm = DummyE2ELLMService()
    embedding = DummyEmbeddingService(dimension=384)
    parser = PlainTextParser()

    from src.application import RaptorEngine
    from src.infrastructure.clustering import UMAPGMMClusteringStrategy
    raptor = RaptorEngine(llm=llm, clustering_strategy=UMAPGMMClusteringStrategy())

    pipeline = IngestionPipeline(llm=llm, embedding=embedding, text_parser=parser, raptor_engine=raptor, fast_model_name="default")

    raw_text = (
        "Artificial Intelligence (AI) is rapidly evolving. It promises to revolutionize many industries. "
        "However, cognitive load theory suggests humans might struggle to keep up with the pace of new information."
    )

    chunks = await pipeline.process_document(raw_text.encode("utf-8"), "ai_article.txt")

    # Assert basic success
    assert len(chunks) > 0
    assert all(isinstance(c, SemanticChunk) for c in chunks)
    assert all(c.id is not None for c in chunks)
    assert all(len(c.embedding) == 384 for c in chunks)

    # Assert AI orchestration
    for chunk in chunks:
        assert "MockEntityA" in chunk.metadata.extracted_entities
        assert chunk.metadata.time_axis == "Present"


@pytest.mark.asyncio
async def test_uat_03_02_semantic_boundary_adherence() -> None:
    """UAT-03-02: Semantic Boundary Adherence"""
    llm = DummyE2ELLMService()
    embedding = DummyEmbeddingService(dimension=384)
    parser = PlainTextParser()

    from src.application import RaptorEngine
    from src.infrastructure.clustering import UMAPGMMClusteringStrategy
    raptor = RaptorEngine(llm=llm, clustering_strategy=UMAPGMMClusteringStrategy())

    pipeline = IngestionPipeline(llm=llm, embedding=embedding, text_parser=parser, raptor_engine=raptor, fast_model_name="default")

    long_sentence = (
        "This is a very long sentence that discusses the complexities of natural language processing "
        "and how it relates to cognitive load theory without being abruptly cut off. "
        "Here is another sentence."
    )

    chunks = await pipeline.process_document(long_sentence.encode("utf-8"), "long_sentence.txt")

    # Ensure it's not cut mid-word arbitrarily
    chunk_texts = [c.content for c in chunks]
    assert any(
        "cognitive load theory without being abruptly cut off." in text for text in chunk_texts
    )
    # Ensure second sentence is kept intact or properly split
    assert any("Here is another sentence." in text for text in chunk_texts)


@pytest.mark.asyncio
async def test_uat_03_03_strict_domain_validation_enforcement() -> None:
    """UAT-03-03: Strict Domain Validation Enforcement"""
    llm = DummyE2ELLMService()
    # Intentionally misconfigured faulty embedding service
    faulty_embedding = DummyEmbeddingService(dimension=3)
    parser = PlainTextParser()

    from src.application import RaptorEngine
    from src.infrastructure.clustering import UMAPGMMClusteringStrategy
    raptor = RaptorEngine(llm=llm, clustering_strategy=UMAPGMMClusteringStrategy())

    pipeline = IngestionPipeline(llm=llm, embedding=faulty_embedding, text_parser=parser, raptor_engine=raptor, fast_model_name="default")

    raw_text = "Standard text document."

    with pytest.raises(ValidationError) as excinfo:
        await pipeline.process_document(raw_text.encode("utf-8"), "test.txt")

    assert "Embedding length 3 is invalid" in str(excinfo.value)
    # The validation originates from SemanticChunk
    assert "SemanticChunk" in str(excinfo.traceback) or "SemanticChunk" in str(excinfo)
