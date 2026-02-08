# Cycle 03 Specification: Summarization Engine (OpenRouter & CoD)

## 1. Summary

Cycle 03 focuses on the "Brain" of the system: the summarization agent. This component is responsible for taking a cluster of related text chunks and synthesizing them into a dense, high-quality summary. We will integrate with **OpenRouter** to leverage cost-effective models like **Gemini 1.5 Flash** for bulk processing and more capable models like **DeepSeek V3** or **GPT-4o** for higher-level reasoning. The core technique implemented here is the **Chain of Density (CoD)** prompting strategy, which iteratively refines the summary to include more entities without increasing length.

## 2. System Architecture

New files for LLM interaction and agent logic.

```
.
├── dev_documents/
├── src/
│   └── matome/
│       ├── ...
│       ├── agents/
│       │   ├── __init__.py
│       │   └── **summarizer.py** # OpenRouter Client & CoD Logic
│       └── ...
├── tests/
│   └── **test_summarizer.py**
└── pyproject.toml                # Added langchain-openai
```

## 3. Design Architecture

### 3.1. Summarization Agent (`src/matome/agents/summarizer.py`)

*   **Class**: `SummarizationAgent`
*   **Attributes**:
    *   `llm`: `ChatOpenAI` (configured for OpenRouter base_url)
    *   `model_name`: `str` (default: `google/gemini-flash-1.5`)
*   **Method**: `summarize(context: str) -> str`
    *   Constructs the CoD prompt.
    *   Calls the LLM.
    *   Parses the final dense summary from the response.

### 3.2. Chain of Density (CoD) Prompt

The prompt template (based on the `ALL_SPEC.md` requirement) will be embedded in `summarizer.py`.

```python
COD_TEMPLATE = """
The following are chunks of text from a larger document, grouped by topic:
{context}

Please generate a high-density summary following these steps:
1. Create an initial summary (~400 chars).
2. Identify missing entities (names, numbers, terms) from the source.
3. Rewrite the summary to include these entities without increasing length.
4. Repeat 3 times.
Output ONLY the final, densest summary.
"""
```

## 4. Implementation Approach

1.  **Dependency**:
    *   Add `langchain-openai` to `pyproject.toml`.
2.  **Configuration**:
    *   Update `src/matome/config.py` to read `OPENROUTER_API_KEY` from environment variables.
3.  **Agent Implementation**:
    *   Implement `SummarizationAgent`.
    *   Add a `_call_llm` method with retry logic (using `tenacity` or LangChain's built-in retries).
4.  **Prompt Engineering**:
    *   Refine the CoD prompt to ensure it works well with Gemini 1.5 Flash (which may be verbose).
    *   Ensure the output is strictly the final summary (or parse it out if the model outputs the chain of thought).

## 5. Test Strategy

### 5.1. Unit Testing
*   **Target**: `src/matome/agents/summarizer.py`
    *   **Test Case**: Mock the `ChatOpenAI.invoke` method. Verify that the correct prompt is sent (substituting `{context}`).
    *   **Test Case**: verify that if the API fails (e.g., 503 error), the agent retries (mocking the exception).

### 5.2. Integration Testing (Mock Mode)
*   **Scenario**:
    *   Set `OPENROUTER_API_KEY` to "mock".
    *   The `SummarizationAgent` should detect this and return a static string "Summary of [context...]" instead of calling the API.
    *   This allows testing the pipeline flow without spending credits.
