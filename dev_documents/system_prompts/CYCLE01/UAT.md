# Cycle 01: User Acceptance Testing (UAT)

## 1. Test Scenarios

These scenarios verify that the `SummarizationAgent` has been successfully refactored to support the **Prompt Strategy Pattern** without breaking existing functionality.

### Scenario 1: Default Strategy (Backward Compatibility)
**Priority**: High
**Goal**: Ensure that calling `summarize` without arguments still works as expected (using the default `BaseSummaryStrategy`).
- **Steps**:
  1. Instantiate `SummarizationAgent` with a valid configuration.
  2. Call `agent.summarize("This is a test text.")`.
  3. Verify that a summary is returned.
  4. Verify (via logging or mock) that the prompt used was the standard summarization prompt.

### Scenario 2: Wisdom Strategy Injection (L1)
**Priority**: Critical
**Goal**: Verify that the agent can generate a "Wisdom" style summary when explicitly requested.
- **Steps**:
  1. Instantiate `SummarizationAgent`.
  2. Instantiate `WisdomStrategy`.
  3. Call `agent.summarize(text, strategy=wisdom_strategy)`.
  4. Verify that the prompt sent to the LLM includes key phrases like "aphorism" or "20-50 characters".

### Scenario 3: Knowledge Strategy Injection (L2)
**Priority**: High
**Goal**: Verify that the agent can generate a "Knowledge" style summary.
- **Steps**:
  1. Instantiate `SummarizationAgent`.
  2. Instantiate `KnowledgeStrategy`.
  3. Call `agent.summarize(text, strategy=knowledge_strategy)`.
  4. Verify that the prompt asks for "underlying mechanisms" or "frameworks".

### Scenario 4: Information Strategy Injection (L3)
**Priority**: High
**Goal**: Verify that the agent can generate an "Action" style summary.
- **Steps**:
  1. Instantiate `SummarizationAgent`.
  2. Instantiate `InformationStrategy`.
  3. Call `agent.summarize(text, strategy=information_strategy)`.
  4. Verify that the prompt asks for "action plan", "checklist", or "how-to".

## 2. Behavior Definitions (Gherkin)

### Feature: Strategy-Based Prompt Generation

**Scenario: Default Execution**
  GIVEN a standard `SummarizationAgent`
  WHEN I call `summarize(text)` with no strategy
  THEN the agent should use `BaseSummaryStrategy`
  AND the resulting prompt should be a standard summary request.

**Scenario: Wisdom Generation**
  GIVEN a standard `SummarizationAgent`
  AND a `WisdomStrategy` instance
  WHEN I call `summarize(text, strategy=WisdomStrategy)`
  THEN the resulting prompt must contain instructions for "conciseness" and "abstraction"
  AND the prompt must strictly limit character count (e.g., "Max 50 chars").

**Scenario: Knowledge Generation**
  GIVEN a standard `SummarizationAgent`
  AND a `KnowledgeStrategy` instance
  WHEN I call `summarize(text, strategy=KnowledgeStrategy)`
  THEN the resulting prompt must contain instructions to identify "Mental Models" or "Frameworks".

**Scenario: Information Generation**
  GIVEN a standard `SummarizationAgent`
  AND an `InformationStrategy` instance
  WHEN I call `summarize(text, strategy=InformationStrategy)`
  THEN the resulting prompt must contain instructions to generate "Action Items" or "Checklists".
