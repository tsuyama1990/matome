import pytest
from pydantic import ValidationError

from src.application import IngestionPipeline
from src.infrastructure.test_services import (
    FallbackEmbeddingService,
    PlainTextParser,
    SafeTestLLMService,
)
from src.interfaces.dependencies import LLMProtocol
from tests.unit.test_raptor_engine import FallbackSemanticClusterer


class PromptSpyLLMService(LLMProtocol):
    """Spy LLM service that records all prompts by wrapping another LLMProtocol via composition."""

    def __init__(self, wrapped_llm: LLMProtocol) -> None:
        self._wrapped_llm = wrapped_llm
        self.recorded_prompts: list[str] = []

    async def generate_text(self, prompt: str, model: str) -> str:
        self.recorded_prompts.append(prompt)
        return await self._wrapped_llm.generate_text(prompt, model)

    async def generate(self, prompt: str) -> str:
        self.recorded_prompts.append(prompt)
        return await self._wrapped_llm.generate(prompt)


@pytest.mark.asyncio
async def test_uat_04_01_hierarchical_tree_construction_fallback_mode() -> None:
    """
    Scenario ID: UAT-04-01
    Title: Hierarchical Tree Construction (Fallback Mode)
    """
    base_llm = SafeTestLLMService()
    llm = PromptSpyLLMService(wrapped_llm=base_llm)
    embedding = FallbackEmbeddingService(dimension=384)
    parser = PlainTextParser()

    from src.application import RaptorEngine

    raptor = RaptorEngine(
        llm=llm,
        clustering_strategy=FallbackSemanticClusterer(
            fallbacked_output={0: [0, 1], 1: [2, 3], 2: [4, 5]}
        ),
    )

    pipeline = IngestionPipeline(
        llm=llm,
        embedding=embedding,
        text_parser=parser,
        raptor_engine=raptor,
        fast_model_name="default",
    )

    raw_text = (
        "Chunk one text. Chunk two text. Chunk three text. "
        "Chunk four text. Chunk five text. Chunk six text."
    )

    # Let the pipeline split by sentences, so we get 6 sentences -> 2 chunks if spacy groups 5.
    # To ensure 6 chunks, we must format it so spacy isn't loaded or bypass the 5-sentence grouping.
    # We will use exactly 6 distinct large sentences and disable the spacy nlp model explicitly.
    pipeline._nlp = None

    doc = await pipeline.build_enriched_document(raw_text.encode("utf-8"), "test.txt")

    # Verify document schema validity and counts
    assert doc is not None
    assert len(doc.chunks) == 6
    assert len(doc.raptor_nodes) == 3

    # Assert children mapped according to fallbacked grouping
    assert "Test Summary or Question." in doc.raptor_nodes[0].summarized_content
    assert len(doc.raptor_nodes[0].children_ids) == 2
    assert set(doc.raptor_nodes[0].children_ids) == {str(doc.chunks[0].id), str(doc.chunks[1].id)}


@pytest.mark.asyncio
async def test_uat_04_02_chain_of_density_prompt() -> None:
    """
    Scenario ID: UAT-04-02
    Title: Chain of Density Prompt Generation
    """
    base_llm = SafeTestLLMService()
    spy_llm = PromptSpyLLMService(wrapped_llm=base_llm)
    embedding = FallbackEmbeddingService(dimension=384)
    parser = PlainTextParser()

    from src.application import RaptorEngine

    raptor = RaptorEngine(
        llm=spy_llm, clustering_strategy=FallbackSemanticClusterer(fallbacked_output={0: [0]})
    )
    pipeline = IngestionPipeline(
        llm=spy_llm,
        embedding=embedding,
        text_parser=parser,
        raptor_engine=raptor,
        fast_model_name="default",
    )

    raw_text = "Some text."
    await pipeline.build_enriched_document(raw_text.encode("utf-8"), "test.txt")

    # Prompt Spy checks
    assert len(spy_llm.recorded_prompts) > 0
    # The first prompts are for metadata extraction, the final one is the CoD prompt.
    cod_prompt = spy_llm.recorded_prompts[-1]

    # Verify the specific instructions from the specification are passed to the AI
    assert "Summarize this text" in cod_prompt
    assert "iteratively rewrite" in cod_prompt
    assert "missing entities" in cod_prompt


@pytest.mark.asyncio
async def test_uat_04_03_tree_relational_integrity_and_schema() -> None:
    """
    Scenario ID: UAT-04-03
    Title: Tree Relational Integrity and Schema Enforcement
    """
    llm = SafeTestLLMService()
    embedding = FallbackEmbeddingService(dimension=384)
    parser = PlainTextParser()

    from src.application import RaptorEngine

    raptor = RaptorEngine(
        llm=llm, clustering_strategy=FallbackSemanticClusterer(fallbacked_output={0: [0, 1]})
    )
    pipeline = IngestionPipeline(
        llm=llm,
        embedding=embedding,
        text_parser=parser,
        raptor_engine=raptor,
        fast_model_name="default",
    )

    raw_text = "Data one. Data two."
    pipeline._nlp = None
    doc = await pipeline.build_enriched_document(raw_text.encode("utf-8"), "test.txt")

    # Verify Relational Consistency (no dangling pointers)
    chunk_ids = {str(c.id) for c in doc.chunks}
    for node in doc.raptor_nodes:
        for child_id in node.children_ids:
            assert child_id in chunk_ids

    # Verify Schema Enforcement (extra forbid check)
    with pytest.raises((ValueError, AttributeError, ValidationError)):
        doc.raptor_nodes[0].invalid_field = "test"  # type: ignore[attr-defined]
