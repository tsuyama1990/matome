# CYCLE 05: Learning Engine & SQ3R Interactions - UAT Plan

## Summary
The User Acceptance Testing (UAT) for Cycle 05 validates the interactive "gamification" core of the `matome` platform. This cycle introduces the SQ3R (Survey, Question, Read, Recite, Review) engine, which actively engages the user rather than allowing passive reading. The UAT scenarios ensure that the system can dynamically generate relevant questions based on hidden document content, accurately evaluate a user's free-text answers using AI, and correctly manage the user's progress (unlocking nodes) based on those evaluations.

This UAT will be implemented in the `tutorials/UAT_AND_TUTORIAL.py` Marimo notebook. It will heavily utilize "Mock Mode" to simulate the AI's role as a tutor/judge deterministically. By verifying this interaction loop, we ensure the product fulfills its mission to "transform the pain of active learning into a pleasurable game of territory acquisition" (PRD 2.2) while maintaining strict data integrity and architectural boundaries.

## Test Scenarios

### Scenario ID: UAT-05-01
**Priority:** High
**Title:** Contextual Question Generation (Mock Mode)
**Description:** This scenario verifies that the application can take a locked section of the document tree (`RaptorNode`) and prompt the AI to generate a relevant question about its hidden content. It ensures the prompt construction correctly includes the necessary context and difficulty parameters.

### Scenario ID: UAT-05-02
**Priority:** High
**Title:** AI Answer Evaluation and Node Unlocking
**Description:** This scenario tests the critical evaluation loop. It simulates a user submitting an answer to an unlock question and verifies that the system correctly orchestrates the AI to judge the answer against the node's actual content. It ensures that only a "correct" evaluation results in the node being marked as unlocked in the user's progress state.

### Scenario ID: UAT-05-03
**Priority:** Medium
**Title:** User Progress State Persistence and Constraints
**Description:** This scenario validates the `LearningProgress` domain model. It ensures that a user's progress (which nodes are unlocked) is accurately tracked and strictly adheres to the schema constraints, preventing invalid state modifications (like unlocking non-existent nodes or adding arbitrary data to the session).

## Behavior Definitions

### UAT-05-01: Contextual Question Generation (Mock Mode)
**GIVEN** an application configured with a `PromptSpyLLMService` (which records incoming prompts) registered in the `DIContainer`.
**AND GIVEN** a `RaptorNode` object representing a locked section of a document, containing the summarized text: "The capital of France is Paris, known for the Eiffel Tower."
**WHEN** the `SQ3REngine` is instructed to generate a "factual" difficulty question for this node.
**THEN** the `PromptSpyLLMService` must record the exact prompt sent to the AI.
**AND** inspecting this recorded prompt must confirm that it contains both the source text ("The capital of France is Paris...") and explicit instructions indicating the requested difficulty level ("factual"). This proves the engine successfully parameterized the AI request based on the domain context.

### UAT-05-02: AI Answer Evaluation and Node Unlocking
**GIVEN** an initialized `SQ3REngine` and a `LearningProgress` object for a new user (where a specific `node_123` is currently locked).
**AND GIVEN** the application is configured with a `MockEvaluationLLMService` that can be deterministically set to return either "YES" (correct) or "NO" (incorrect).
**WHEN** the user submits the answer "London" and the mock service is configured to evaluate it as "NO".
**THEN** the `SQ3REngine.evaluate_answer` method must return `False`.
**AND** the `node_123` must remain absent from the `LearningProgress.unlocked_node_ids` set.
**WHEN** the user subsequently submits the answer "Paris" and the mock service is configured to evaluate it as "YES".
**THEN** the `SQ3REngine.evaluate_answer` method must return `True`.
**AND WHEN** the system processes this successful result.
**THEN** the `node_123` must be successfully added to the `LearningProgress.unlocked_node_ids` set, proving the state transition logic functions correctly based on AI evaluation.

### UAT-05-03: User Progress State Persistence and Constraints
**GIVEN** an active `LearningProgress` object tracking a user's session for a specific document.
**WHEN** the application successfully evaluates an answer and attempts to update the state by adding a valid `node_id` to the `unlocked_node_ids` set.
**THEN** the operation must succeed, and the node must be recorded as unlocked.
**AND WHEN** a hypothetical bug in the application attempts to illegally attach unstructured data to the progress object (e.g., `progress.temporary_score = 100`).
**THEN** the Pydantic runtime must immediately raise a `ValidationError` (or similar strict rejection), enforcing the `extra="forbid"` configuration. This guarantees that the user's learning state remains pristine and predictable, preventing corrupted sessions.