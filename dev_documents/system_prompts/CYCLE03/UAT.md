# Cycle 03 User Acceptance Testing (UAT) Plan

## 1. Test Scenarios

### Scenario 08: OpenRouter Connection (Priority: High)
*   **Goal**: Ensure the system can communicate with the OpenRouter API.
*   **Inputs**: A valid `OPENROUTER_API_KEY`. A simple prompt "Hello, world!".
*   **Expected Outcome**: The `SummarizationAgent` successfully receives a response (e.g., "Hello! How can I help you?").
*   **Note**: This requires Real Mode.

### Scenario 09: Chain of Density Behavior (Priority: High)
*   **Goal**: Ensure the CoD prompt generates dense summaries.
*   **Inputs**: A verbose text about a specific topic (e.g., "The history of the iPhone").
*   **Expected Outcome**: The resulting summary is significantly shorter than the input but retains key dates (2007), names (Steve Jobs), and product names (iPhone 3G).

### Scenario 10: Error Handling & Retries (Priority: Medium)
*   **Goal**: Ensure the system is robust against transient API failures.
*   **Inputs**: Simulating a network error or 503 response.
*   **Expected Outcome**: The agent retries automatically before raising a final exception.

## 2. Behavior Definitions (Gherkin)

```gherkin
Feature: Summarization Agent

  Scenario: Generating a summary using CoD
    GIVEN a cluster of related text chunks
    WHEN the SummarizationAgent processes the cluster
    THEN it should send a request to the configured LLM model
    AND the response should contain a condensed summary
    AND the summary should include key entities from the chunks

  Scenario: Handling API failures
    GIVEN the external LLM API is temporarily unavailable
    WHEN the agent attempts to summarize
    THEN it should wait and retry the request
    AND eventually return a result or a structured error
```
