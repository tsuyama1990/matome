# System Architecture: Long Context Summarization System

## 1. Summary

The **Long Context Summarization System** is a next-generation document processing platform designed to overcome the inherent limitations of Large Language Models (LLMs) when dealing with extensive texts. Traditional approaches often suffer from the "Lost-in-the-Middle" phenomenon, where information in the middle of a long context is overlooked, and "Hallucinations," where the model invents facts. This system addresses these challenges by implementing a "System Engineering" approach rather than relying solely on prompt engineering.

The core philosophy of this system is **"Structure, Abstract, Verify."** Instead of feeding a massive text block into an LLM, the system decomposes the document into semantically meaningful chunks, clusters them based on vector similarity, and recursively summarizes them to build a hierarchical tree of information. This method is known as **RAPTOR (Recursive Abstractive Processing for Tree-Organized Retrieval)**. By combining this with **GraphRAG** concepts, which map relationships between entities, the system ensures a holistic understanding of the document structure.

Key innovations include:
1.  **Japanese-Optimized Semantic Chunking**: Unlike standard splitters that break text at arbitrary character limits, our system uses regex-based logic tailored for Japanese punctuation and sentence structures to preserve semantic integrity.
2.  **Cost-Effective Routing**: The architecture intelligently routes tasks between lightweight models (e.g., Gemini 1.5 Flash) for bulk processing and reasoning models (e.g., DeepSeek V3 or GPT-4o) for high-level synthesis, optimizing both cost and quality.
3.  **Iterative Verification**: Through **Chain of Verification (CoVe)** and **Context-Aware Hierarchical Merging (CAHM)**, every summary is cross-referenced with the source text to minimize hallucinations.
4.  **Human-in-the-Loop KJ Method**: The system outputs data compatible with **Obsidian Canvas**, allowing users to visually inspect, rearrange, and refine the AI-generated structure, mimicking the traditional KJ method for idea organization.

This architecture transforms the summarization task from a "black box" generation into a transparent, verifiable, and interactive process, making it suitable for high-stakes domains like financial analysis, legal review, and academic research.

## 2. System Design Objectives

The primary goal is to build a robust, scalable, and cost-efficient summarization engine that rivals human-level comprehension for long documents.

### 2.1. Goals
*   **Overcome Context Limits**: Successfully process documents exceeding 100,000 tokens without losing critical details.
*   **Mitigate Hallucinations**: Achieve a hallucination rate of less than 5% through rigorous verification steps.
*   **Preserve Narrative Structure**: Ensure the summary reflects the logical flow and hierarchy of the original document, not just a bag of isolated facts.
*   **Interactive Usability**: Provide a "Mock Mode" for testing and an "Interactive Mode" where users can refine the intermediate results (KJ Method).

### 2.2. Constraints
*   **Cost Efficiency**: The processing cost per document must be kept low by leveraging cheaper models for the heavy lifting (chunking/clustering).
*   **Language Support**: Primary focus on Japanese text, handling specific linguistic nuances (particles, lack of spaces).
*   **Execution Time**: The full pipeline for a standard book-length PDF should complete within a reasonable timeframe (e.g., under 10 minutes).
*   **Dependency Management**: Strict adherence to the provided tech stack (LangChain, UMAP, scikit-learn, spacy).

### 2.3. Success Criteria
*   **Table of Contents Coverage**: The generated summary must cover at least 70% of the topics found in the original document's table of contents.
*   **Structural Integrity**: The recursive tree structure must effectively capture both high-level themes and supporting details.
*   **User Satisfaction**: The "Aha! Moment" tutorial must demonstrate a clear value proposition to new users.

## 3. System Architecture

The system follows a pipeline architecture, transforming raw text into a structured knowledge tree.

### 3.1. Components
1.  **Ingestion Layer**: Handles reading of source files (PDF, TXT). It normalizes text and removes artifacts.
2.  **Chunking Engine**: Splits text into semantic units using Japanese-specific regex and embedding similarity.
3.  **Embedding & Clustering Service**: Converts chunks into vector embeddings (using `multilingual-e5`) and groups them using UMAP (dimensionality reduction) and GMM (Gaussian Mixture Models).
4.  **Summarization Agent**: A sophisticated agent that uses the "Chain of Density" prompt technique to generate dense, information-rich summaries for each cluster. It uses OpenRouter to access optimal models.
5.  **Recursive Controller**: Manages the RAPTOR loop—taking summaries, treating them as new chunks, and repeating the clustering/summarization process until a root node is reached.
6.  **Verification Module**: Checks for entity overlap and consistency between source and summary.
7.  **Presentation Layer**: Formats the output into Markdown and Obsidian Canvas JSON.

### 3.2. Data Flow
1.  **Input**: Raw Document -> **Text Normalizer** -> Clean Text.
2.  **Process**: Clean Text -> **Semantic Chunker** -> Chunks.
3.  **Vectorization**: Chunks -> **Embedding Model** -> Vectors.
4.  **Structure**: Vectors -> **UMAP/GMM** -> Clusters.
5.  **Synthesis**: Clusters -> **LLM (CoD)** -> Summaries (Level N).
6.  **Recursion**: Summaries (Level N) -> **Loop back to Vectorization** -> Summaries (Level N+1).
7.  **Output**: Final Tree -> **Formatter** -> Markdown / JSON.

### 3.3. Architecture Diagram

```mermaid
graph TD
    User[User Input] -->|PDF/TXT| Ingest[Ingestion Layer]
    Ingest -->|Clean Text| Chunk[Chunking Engine]
    Chunk -->|Semantic Chunks| Embed[Embedding Service]
    Embed -->|Vectors| Cluster[Clustering (UMAP/GMM)]
    Cluster -->|Cluster Indices| Summarizer[Summarization Agent (CoD)]
    Summarizer -->|Cluster Summaries| Recursion{Is Root?}
    Recursion -- No --> Embed
    Recursion -- Yes --> Verify[Verification Module]
    Verify -->|Verified Tree| Format[Presentation Layer]
    Format -->|Markdown| Out1[summary_all.md]
    Format -->|Obsidian Canvas| Out2[summary_kj.md]
```

## 4. Design Architecture

The codebase is structured to separate concerns and enforce type safety using Pydantic.

### 4.1. File Structure (ASCII Tree)
```
.
├── dev_documents/          # Documentation and Prompts
├── src/
│   └── matome/             # Main Package
│       ├── __init__.py
│       ├── cli.py          # Command Line Interface
│       ├── config.py       # Configuration & Environment Variables
│       ├── domain/         # Domain Models (Pydantic)
│       │   ├── __init__.py
│       │   ├── models.py   # Document, Chunk, Cluster, SummaryNode
│       │   └── schemas.py  # Input/Output Schemas
│       ├── engines/        # Core Logic Engines
│       │   ├── __init__.py
│       │   ├── chunker.py  # Semantic Chunking Logic
│       │   ├── cluster.py  # UMAP + GMM Logic
│       │   ├── embedder.py # Embedding Generation
│       │   └── raptor.py   # Recursive Controller
│       ├── agents/         # LLM Agents
│       │   ├── __init__.py
│       │   ├── summarizer.py # CoD Prompts & OpenRouter Client
│       │   └── verifier.py   # Hallucination Check
│       ├── utils/          # Utilities
│       │   ├── __init__.py
│       │   ├── text.py     # Japanese Text Helpers
│       │   └── io.py       # File Reading/Writing
│       └── exporters/      # Output Formatters
│           ├── __init__.py
│           ├── markdown.py
│           └── obsidian.py
├── tests/                  # Unit and Integration Tests
├── pyproject.toml          # Project Configuration
└── README.md               # Entry Point
```

### 4.2. Key Data Models (Pydantic)
*   `Chunk`: Represents a text segment with metadata (source, index) and its vector embedding.
*   `Cluster`: A collection of `Chunk` objects identified by the GMM.
*   `SummaryNode`: A node in the RAPTOR tree containing the summary text, references to child chunks/nodes, and its level in the hierarchy.
*   `DocumentTree`: The complete hierarchical structure, holding the root node and all levels.

### 4.3. Class/Function Overview
*   **`SemanticChunker.split_text(text: str) -> List[Chunk]`**: Implements the regex-based splitting and semantic merging.
*   **`ClusterEngine.perform_clustering(embeddings: np.ndarray) -> List[int]`**: Runs UMAP reduction followed by GMM to assign cluster labels.
*   **`SummarizationAgent.summarize(context: str) -> str`**: Sends the prompt to OpenRouter with Chain of Density instructions.
*   **`RaptorEngine.run(text: str) -> DocumentTree`**: Orchestrates the entire recursive process.

## 5. Implementation Plan

The development is divided into 6 sequential cycles.

*   **CYCLE01: Foundation & Text Processing**
    *   **Goal**: Establish the project structure and implement the Japanese-optimized chunking logic.
    *   **Features**: Project skeleton, Pydantic models, Text Ingestion, Semantic Chunking with Regex.
*   **CYCLE02: Embedding & Clustering Core**
    *   **Goal**: Implement the mathematical core for organizing text.
    *   **Features**: `multilingual-e5` integration, UMAP dimensionality reduction, GMM soft clustering.
*   **CYCLE03: Summarization Engine**
    *   **Goal**: Connect to LLMs and implement the summarization prompts.
    *   **Features**: OpenRouter API Client, Chain of Density (CoD) Prompt Templates, Basic Summarization Function.
*   **CYCLE04: Recursive Summarization (RAPTOR)**
    *   **Goal**: Build the recursive logic to create the knowledge tree.
    *   **Features**: RAPTOR loop implementation, linking chunks to summaries, creating the `DocumentTree` structure, generating `summary_all.md`.
*   **CYCLE05: KJ Method & Visualization**
    *   **Goal**: Enable visual interaction with the results.
    *   **Features**: Logic to map the tree to a 2D canvas, Obsidian Canvas JSON exporter, generating `summary_kj.md`.
*   **CYCLE06: Verification & Final Polish**
    *   **Goal**: Ensure quality and usability.
    *   **Features**: Verification module (CoVe), CLI improvements (progress bars, model selection), End-to-End testing.

## 6. Test Strategy

Testing will be rigorous, focusing on component correctness and system coherence.

*   **Unit Testing**:
    *   Each module (`chunker`, `cluster`, `embedder`) will have dedicated test files.
    *   We will mock external API calls (OpenAI/OpenRouter) to ensure tests are fast and deterministic.
    *   Specific tests for Japanese regex patterns to ensure they don't break sentences unnaturally.
*   **Integration Testing**:
    *   Test the interaction between Chunker and Embedder.
    *   Test the RAPTOR loop with a small, synthetic text dataset to verify the tree construction logic without incurring high API costs.
*   **User Acceptance Testing (UAT)**:
    *   We will use the "Mock Mode" for initial UAT to verify the flow.
    *   The "Real Mode" UAT will use the provided "Company Shikiho" text to verify the quality of the summary against the 70% coverage criteria.
*   **Regression Testing**:
    *   Ensure that changes in the prompt templates do not degrade the summary quality (checked via manual review of key outputs).
