# CYCLE 05: Learning Engine & SQ3R Interactions

## Summary
With the robust `EnrichedDocument` and its navigable RAPTOR tree generated in Cycle 04, Cycle 05 shifts focus entirely to the user's interactive learning experience. The core objective of this cycle is to implement the "Frictionless SQ3R Automation" detailed in the PRD (FR-3). This means building the backend logic that transforms passive reading into an active, game-like process by forcing the user to answer AI-generated questions before unlocking new sections of the document tree.

We will develop the `SQ3REngine` application service. This engine is responsible for two primary operations: first, dynamically generating a contextual "Unlock Question" based on the hidden content of a `RaptorNode` using the LLM; and second, evaluating the user's answer (via the LLM) to determine if it demonstrates sufficient understanding to unlock the node. We will also implement the state management required to track a user's progress through the document (which nodes are locked, which are unlocked). This cycle breathes life into the static data structures, fulfilling the product's promise to dramatically increase learning retention through active recall.

## System Architecture

The architecture for Cycle 05 resides primarily within the Application Layer (`src/application/`) and introduces state management models within the Domain Layer (`src/domain_models/user_session.py`). The `SQ3REngine` orchestrates these interactions. It heavily utilizes the `LLMProtocol` (injected via the `DIContainer`) to both generate questions and evaluate answers. It interacts with the existing `EnrichedDocument` (specifically `RaptorNode`s) to understand the context of what needs to be learned, and it updates the `LearningProgress` state based on user actions.

```text
matome/
├── src/
│   ├── **domain_models/**
│   │   ├── document.py        (Existing)
│   │   ├── **user_session.py**    (NEW: LearningProgress, UnlockAttempt)
│   ├── interfaces/
│   │   ├── llm_protocol.py    (Existing)
│   ├── **application/**
│   │   ├── **learning.py**        (NEW: SQ3REngine)
```

## Design Architecture

This cycle focuses on interactive logic and user state management.

### 1. `src/domain_models/user_session.py`
*   **`UnlockAttempt`**: A Pydantic model representing a single attempt by a user to unlock a node. It should contain `node_id: str`, `user_answer: str`, `is_correct: bool`, and `timestamp: datetime`. It must forbid extra fields.
*   **`LearningProgress`**: A Pydantic model tracking a user's overall progress on a specific document. It contains `document_id: UUID`, `unlocked_node_ids: set[str]`, and `history: list[UnlockAttempt]`. This model represents the mutable state of the user's learning journey and is crucial for the UI to determine which parts of the tree to display. It must forbid extra fields.

### 2. `src/application/learning.py`
*   **`SQ3REngine`**: The core application service for interactive learning.
    *   **Dependencies**: Requires `LLMProtocol` injected via `__init__`.
    *   **`generate_question(node: RaptorNode, difficulty: str = "medium") -> str`**: This method takes a locked `RaptorNode`. It extracts the `summarized_content` (the text the user hasn't seen yet). It constructs a prompt instructing the LLM to generate a question based on this content, tailored to the requested difficulty (e.g., factual recall for "easy", inferential for "hard"). It returns the question string.
    *   **`evaluate_answer(node: RaptorNode, user_answer: str) -> bool`**: This method takes the hidden content of the node and the user's submitted answer. It constructs an evaluation prompt for the LLM (e.g., "Given this source text and this user's answer to a question about it, is the user's answer fundamentally correct or demonstrating understanding? Respond only with 'YES' or 'NO'"). It parses the LLM's response to return a boolean indicating success or failure.
    *   **`unlock_node(progress: LearningProgress, node_id: str) -> LearningProgress`**: A pure function that updates the `LearningProgress` state by adding the `node_id` to the `unlocked_node_ids` set, returning the updated state object.

## Implementation Approach

1.  **Define User Session Models**: Create `src/domain_models/user_session.py`. Define the `UnlockAttempt` and `LearningProgress` Pydantic models with strict validation rules.
2.  **Develop `SQ3REngine`**: Create `src/application/learning.py`. Define the class and inject the `LLMProtocol`.
3.  **Implement Question Generation**: Write `generate_question`. Construct a prompt template (e.g., using `f-strings` or a templating engine if preferred, but keep it simple for now) that includes the `node.summarized_content` and instructions to formulate a question. Call `self.llm.generate_text`. Return the result.
4.  **Implement Answer Evaluation**: Write `evaluate_answer`. Construct an evaluation prompt containing the `node.summarized_content` and the `user_answer`. Crucially, instruct the LLM to provide a binary YES/NO response to make parsing reliable. Call `self.llm.generate_text`. Implement robust parsing logic to interpret the result as a boolean, handling potential variations in the LLM's output (e.g., parsing "Yes, that is correct" as True).
5.  **Implement State Update**: Write the `unlock_node` method to securely update the `LearningProgress` object.

## Test Strategy

Testing Cycle 05 requires careful orchestration of the `DummyLLMService` to simulate both the generation of questions and the evaluation of user answers, ensuring the logic flows correctly without actual AI reasoning.

**Unit Testing Approach (Minimum 300 words):**
We will focus unit tests on the `SQ3REngine` in `src/application/learning.py`. We will inject the `DummyLLMService` from previous cycles.

First, we will test `generate_question`. We will provide a dummy `RaptorNode` with a known `summarized_content` string. We will configure the `DummyLLMService` to return a specific question string (e.g., "What is the capital of France?"). We will call the method and assert it returns exactly that string. Crucially, we must also test the *prompt construction*. We will create a specialized `PromptSpyLLMService` (a variant of the dummy) that records the prompt it receives. We will assert that the prompt sent to the LLM contains the node's `summarized_content` and instructions regarding the requested `difficulty` level, proving the engine correctly parameterizes the AI request.

Next, we will deeply test `evaluate_answer`. This is complex because we rely on the LLM to act as a judge. We will configure the `DummyLLMService` to return "YES" for one test and "NO" for another. We will assert that `evaluate_answer` correctly parses "YES" to `True` and "NO" to `False`. We must also test edge cases in LLM parsing: configure the dummy to return " Yes, absolutely " or "I think no", and ensure the parsing logic robustly handles whitespace and variations to return the correct boolean. As with question generation, we will use the `PromptSpyLLMService` to verify the evaluation prompt contains both the node content and the user's answer.

Finally, we will unit test the state models in `src/domain_models/user_session.py` to ensure `extra="forbid"` is enforced and that updating the `unlocked_node_ids` set in `LearningProgress` works as expected.

**Integration Testing Approach (Minimum 300 words):**
The integration tests for Cycle 05 will simulate a complete user interaction loop using the "Mock Mode" DI container.

We will initialize a `DIContainer` containing the `DummyLLMService` and the `SQ3REngine`. We will also create a dummy `EnrichedDocument` containing at least one `RaptorNode` (node ID "node-1") and initialize a fresh `LearningProgress` object for a simulated user.

The test will perform the following sequence:
1.  **Check Initial State**: Assert that "node-1" is NOT in `progress.unlocked_node_ids`.
2.  **Generate Question**: Call `engine.generate_question(node)`. Assert a question string is returned.
3.  **Attempt Unlock (Failure)**: Simulate the user providing a bad answer. Configure the `DummyLLMService` to return "NO" (or parseable equivalent) for the evaluation call. Call `engine.evaluate_answer(node, "bad answer")`. Assert it returns `False`.
4.  **Verify State (Still Locked)**: Assert that "node-1" is still NOT in `progress.unlocked_node_ids`.
5.  **Attempt Unlock (Success)**: Simulate the user providing a good answer. Configure the `DummyLLMService` to return "YES". Call `engine.evaluate_answer(node, "good answer")`. Assert it returns `True`.
6.  **Update State**: Call `engine.unlock_node(progress, "node-1")`.
7.  **Verify Final State**: Assert that "node-1" IS now present in `progress.unlocked_node_ids`.

This comprehensive integration test proves that the application correctly orchestrates the LLM to facilitate the SQ3R loop and accurately manages the user's learning state, fulfilling the core interactive requirements of the PRD while strictly adhering to the architectural guidelines.