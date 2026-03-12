# User Acceptance Test (UAT) Scenario & Tutorial Plan

## 1. Test Scenarios

The following scenarios are designed to act both as formal User Acceptance Tests (UAT) and engaging tutorials for new users. These scenarios are intended to validate the core value propositions of the matome platform, specifically focusing on the mitigation of cognitive load and the seamless transition from passive reading to active, structured output generation. We use `marimo` to provide a reproducible, interactive Python notebook experience that allows stakeholders to tangibly experience the 'Aha! Moment' without requiring complex local environment setup.

### Scenario ID: UAT-01 - The 'Aha!' Moment for a Product Manager (Quick Start)
**Priority:** High
**Description:** A Product Manager (PdM) or Systems Engineer is tasked with deciphering a dense, unstructured legacy system manual. Their goal is to convert this archaic document into a modern, logically structured workflow without falling victim to the 'As-Is' trap, where inefficient existing processes are merely digitised without critical evaluation.

**Steps:**
1. **Ingestion (Survey Phase):** The user begins by uploading a complex, multi-page text file (e.g., `testfiles/test_text.txt`) that represents a typical convoluted business manual. The platform must rapidly ingest this document, parse the text, and perform semantic chunking. Instead of presenting a daunting wall of text, the system must display an interactive, highly visual tree structure—the RAPTOR graph. This initial view should only show the highest-level conceptual nodes, adhering to the principles of progressive disclosure.
2. **Interaction (Question & Read Phase):** The user selects a locked node on the canvas, perhaps one titled 'Special Approval Processes.' Rather than immediately displaying the contents, the AI actively engages the user by prompting: 'Based on the surrounding context, what specific condition do you think necessitates executive approval instead of standard managerial sign-off?' The user must formulate a hypothesis and submit an answer. Upon submission, the node bursts open with a satisfying visual animation, revealing a highly dense, rigorously summarised text block generated via the Chain of Density (CoD) process.
3. **Active Recall (Recite Phase):** After reading the newly revealed summary, the user is required to actively synthesise the information. The user activates the microphone interface and verbalises the core point: 'Executive approval is strictly required if the project budget exceeds £5000.' The AI evaluates this audio input and responds almost instantly with positive 'Sandwich Feedback,' confirming the correct understanding while gently correcting any minor discrepancies or missing nuances.
4. **Transformation (Pivot KJ Phase):** Having comprehended the raw material, the user clicks the 'Pivot' button. They select a new analytical axis from a dropdown menu, choosing 'Actor vs. State Transition.' The interface immediately and dynamically re-arranges the nodes. The original chapter-based structure of the manual is dismantled, and the nodes physically migrate across the canvas to form a new, logical swimlane workflow layout, clearly separating actor responsibilities.
5. **Export (Production Phase):** Finally, the user clicks the 'Export PRD' button. The system instantly processes the rearranged nodes and downloads a comprehensive Markdown document. This document contains the newly formulated To-Be system requirements and includes a syntactically valid Mermaid.js sequence diagram that visually represents the new workflow.

**Expected Result:** The user experiences immediate relief from the cognitive burden typically associated with reading raw, unstructured text. They feel the tangible excitement of instantly generating a structured, actionable system design from an otherwise impenetrable manual. The seamless progression from input to output validates the platform's core mission of frictionless knowledge transformation.
Additionally, the user must verify the strict latency requirements during this interaction phase. When the user submits the voice transcript, the system must process the audio, evaluate the semantic correctness, and return the Sandwich Feedback within an absolute maximum latency threshold of 2.5 seconds. Should this threshold be exceeded, the test fails, as the core promise of a frictionless flow state has been compromised. Furthermore, the generated Markdown document and Mermaid.js sequence diagram must be rigorously verified against the original legacy manual's intent. If a critical approval step or a specific data transfer constraint defined in the original text is entirely omitted from the final To-Be workflow, the extraction engine must be refined. The test dictates that the system must accurately distinguish between core business rules that must be preserved, and the analogue inefficiencies that should be aggressively stripped away. Finally, the user must confirm that the entire operation, from the initial file upload to the final artifact export, occurred without ever requiring the user to manually highlight text, drag nodes, or type a single line of Markdown code, thereby proving the platform's capacity for fully automated cognitive support.


### Scenario ID: UAT-02 - Multi-Dimensional Analysis for a Consultant (Advanced)
**Priority:** Medium
**Description:** A New Business Developer or Consultant needs to rapidly synthesise vast amounts of disparate information across multiple market reports, competitor analyses, and regulatory documents. Their objective is to discover a unique, non-obvious angle for a high-stakes strategy pitch to upper management, avoiding the superficial conclusions that result from mere skimming.

**Steps:**
1. **Bulk Ingestion (Aggregation Phase):** The user uploads three separate, lengthy documents simultaneously: a macro-economic market trend report, a detailed technical specification of a competitor's product, and a complex legal document outlining impending regulatory changes in the European market. The system must process these in parallel, extracting semantic chunks and Named Entities from all sources without merging them indiscriminately.
2. **Exploration (Navigation Phase):** The system generates a massive, interconnected knowledge tree. The user navigates this complex space using the Semantic Zoom UI. To prevent disorientation, the interface must continuously update an interactive minimap in the corner of the screen. Furthermore, a dynamic breadcrumb trail must remain visible at the top of the canvas, allowing the user to instantly trace their current position back to the overarching root concepts (e.g., 'European Market' > 'Competitor A' > 'Pricing Strategy').
3. **Restructuring (Custom Pivot Phase):** The user recognises that the standard document structures are insufficient for their pitch. They trigger the Pivot KJ engine and define a completely custom analytical axis using natural language: 'Opportunities vs. Threats specifically regarding the new EU data privacy laws.' The system queries the underlying vector database, pulls relevant semantic chunks across all three original documents, and physically reorganises the nodes on the canvas into a custom two-by-two matrix.
4. **Web-Grounding (Verification Phase):** As the user examines the newly formed 'Threats' quadrant, the AI proactively flags a specific node concerning a stringent regulatory penalty. The AI initiates a real-time web search and presents a pop-up suggestion: 'Recent news articles from verified sources indicate that the enforcement of this specific penalty has been delayed by 18 months. Would you like to downgrade the severity of this threat in your matrix?' The user reviews the cited source and accepts the AI's suggestion, dynamically updating the node's status.
5. **Synthesis (Insight Generation):** The user reviews the finalised, externally validated matrix. They use the system to generate an executive summary that highlights the newly discovered opportunities, specifically noting the delayed regulatory threat as a unique strategic advantage against competitors who may be acting on outdated information.

**Expected Result:** The consultant successfully breaks entirely free from the original authors' narrative structures and biases. They generate a completely novel, highly structured, and externally validated insight matrix without ever resorting to manual copy-pasting or switching context between multiple PDF viewers. The platform acts as an intelligent sounding board, significantly elevating the quality of the strategic output.
Furthermore, the consultant must rigorously test the system's ability to seamlessly manage context limits and rate limits during the bulk ingestion phase. Since three distinct, extensive market reports are uploaded simultaneously, the backend infrastructure must accurately queue and distribute the semantic chunking tasks via the `LLMGateway` without triggering HTTP 429 Too Many Requests errors from the OpenRouter API. If the system fails to correctly identify distinct Named Entities (e.g., merging a European regulatory body with a competitor's proprietary software product under the same semantic umbrella), the entire matrix generation fails. The consultant will actively attempt to cause a context collision by deliberately feeding the system highly ambiguous terms that appear across all three documents. The system must prove its resilience by disambiguating these terms based on their respective source document metadata. Finally, during the Web-Grounding phase, the user will verify the authenticity of the AI's provided citations. If the AI hallucinates a news source or incorrectly cites an outdated article regarding the delayed regulatory penalty, the Web-Grounding integration must be deemed unstable. The test demands that all external validations provided by the platform are verifiably anchored to real-world, current data, ensuring that the final strategy pitch presented to upper management is built upon an unshakeable foundation of factual accuracy.


## 2. Behavior Definitions (Gherkin)

This section explicitly defines the behavioural expectations of the matome system using the structured Gherkin syntax (Given-When-Then). These definitions serve as the definitive contract between the product requirements and the technical implementation, ensuring that the system's core capabilities—such as secure document processing, interactive learning enforcement, and multi-dimensional knowledge restructuring—function reliably and predictably. These scenarios are designed to cover both the happy paths of standard user interactions and the critical edge cases, including security boundaries and malformed inputs. By codifying these behaviours, we establish a robust foundation for automated integration testing, enabling continuous validation of the platform's integrity throughout the development lifecycle. The precise language used here dictates the exact state transitions that the underlying domain models (e.g., `Document`, `GraphNode`) must undergo during operation. Furthermore, these definitions enforce the strict architectural rules regarding error handling, dictating that the system must respond with appropriate domain-specific exceptions and clear HTTP status codes when preconditions are not met or external services fail. Ultimately, these Gherkin scenarios guarantee that the final platform will not only meet but demonstrably prove its adherence to the core mission of providing a frictionless, highly secure, and cognitively optimised active learning environment.

### Feature: Secure and Context-Aware Document Processing
```gherkin
FEATURE: As a user, I want to upload complex documents so that the system can securely break them down into digestible semantic chunks without losing deep context or exposing my data to unauthorised access.

  SCENARIO: Uploading a valid text file and generating a RAPTOR tree
    GIVEN the user is authenticated and has a valid API key configured in their profile
    AND the file "testfiles/test_text.txt" exists and contains valid utf-8 encoded text
    WHEN the user submits a POST request to the file upload endpoint with the text file
    THEN the system must return a 202 Accepted status code immediately
    AND the system must initiate a background worker task to process the document
    AND the background task must successfully generate a complete RAPTOR tree composed of GraphNode models
    AND the highest-level root node of the tree must become accessible via the study API endpoint within 10 seconds.

  SCENARIO: Rejecting a malformed file format gracefully
    GIVEN the user is authenticated
    AND the user selects a binary executable file disguised with a ".txt" extension
    WHEN the user attempts to upload the file via the ingestion API
    THEN the system must intercept the request during the validation phase
    AND the system must return a 415 Unsupported Media Type status code
    AND the system must provide a clear JSON error message indicating the invalid file type
    AND no background processing task should be initiated.

  SCENARIO: Preventing Path Traversal Attacks during file retrieval
    GIVEN a malicious payload attempting to read a sensitive system file like "../../etc/passwd"
    WHEN the user submits the payload to the document retrieval endpoint as a document ID
    THEN the API Gateway must strictly validate the input against the expected UUID format
    AND the system must reject the request with a 400 Bad Request status code
    AND the underlying file system must not be accessed
    AND the security event must be logged without exposing the raw payload to the user interface.
```

### Feature: Frictionless Active Learning (SQ3R Enforcement)
```gherkin
FEATURE: As a learner, I want to be actively questioned before reading and required to provide feedback after reading, so that the system forces generative learning and I retain the information in my long-term memory.

  SCENARIO: Successfully unlocking a node with a semantically correct answer
    GIVEN a specific concept node on the user's canvas is currently in a locked state
    WHEN the user sends a request to view the details of that specific node
    THEN the system must respond with an AI-generated question prompt relevant to the node's hidden content
    WHEN the user submits a text answer that matches the semantic intent of the node (evaluated via LLM, not exact keyword matching)
    THEN the system must update the node's state to "unlocked" in the database
    AND the system must return the high-density Chain of Density (CoD) summary text to the frontend for display
    AND the system must trigger a positive visual feedback animation event.

  SCENARIO: Handling a completely incorrect answer gracefully with hints
    GIVEN the user has received a question prompt for a locked node
    WHEN the user submits an answer that is entirely unrelated to the node's semantic content
    THEN the system must retain the node in its locked state
    AND the system must return a gentle, encouraging message indicating the answer was incorrect
    AND the system must provide a progressively easier hint (e.g., revealing the first letter of a key term) to unblock the user's cognition.

  SCENARIO: Reciting information and receiving AI Sandwich Feedback
    GIVEN the user has successfully unlocked and read the CoD summary of a node
    WHEN the user submits an audio transcript summarising the core points of the node
    AND the transcript contains a hallucinated fact that is not present in the original source material
    THEN the Context-Aware Hierarchical Merging (CAHM) engine must detect the discrepancy
    AND the system must return "Sandwich Feedback" that first praises the user for the correct portions of their summary
    AND gently corrects the specific hallucinated fact without using discouraging language.
```

### Feature: Multi-Dimensional Knowledge Restructuring (Pivot KJ)
```gherkin
FEATURE: As an analyst, I want to dynamically rearrange the generated knowledge tree based on new analytical axes, so that I can generate novel insights, business strategies, and technical system requirements.

  SCENARIO: Pivoting a business manual into a System Design Axis
    GIVEN the system has fully processed a document tree representing a standard, chapter-based business manual
    WHEN the user triggers the Pivot KJ engine, selecting the predefined "Actor vs. State Transition" axis
    THEN the system must query the vector database to retrieve relevant chunks across the entire document
    AND the system must map the existing nodes into a new logical structure representing workflow stages
    AND the frontend must receive the new layout coordinates to animate the nodes into a swimlane configuration
    AND the system must successfully generate a syntactically valid Mermaid.js sequence diagram snippet that accurately reflects the new dependencies.

  SCENARIO: Defining and executing a custom natural language axis
    GIVEN a fully processed document tree representing multiple market reports
    WHEN the user submits a custom axis defined as "Compare the short-term risks versus long-term opportunities"
    THEN the LLMGateway must successfully interpret the natural language intent
    AND the system must physically reorganise the nodes on the canvas into a two-by-two matrix structure
    AND the system must preserve all original metadata and links to the source document for every node in the new layout.
```


## 3. Tutorial Strategy

The primary strategy for user acceptance testing and developer onboarding is to provide a completely frictionless, highly interactive experience. We will avoid complex CLI scripts or disjointed test files that require deep contextual knowledge of the codebase. Instead, we will leverage `marimo` to create a single, unified, and visually engaging Python notebook. This approach allows users to verify the core functionalities step-by-step, observing the internal state changes of the system in real-time.

To accommodate diverse testing environments, the tutorial strategy incorporates a dual-mode execution approach:
*   **Mock Mode (CI/CD and No-API-Key Execution):** When executed in a Continuous Integration pipeline or by a user who has not yet configured an OpenRouter API key, the tutorial will automatically default to using `unittest.mock`. It will simulate the responses from the LLM and the Vector Database. This ensures that the logical flow, state transitions, and data transformations of the system can be safely and instantly validated without incurring API costs or failing due to network issues.
*   **Real Mode:** If a valid `OPENROUTER_API_KEY` environment variable is detected during execution, the tutorial will seamlessly switch to hitting the real, live infrastructure. This mode proves the end-to-end integration works exactly as designed in a production-like scenario.

## 4. Tutorial Plan

To ensure absolute simplicity and ease of verification, we mandate the creation of a **SINGLE** interactive Marimo notebook file. Splitting the tutorial across multiple files introduces unnecessary cognitive load and execution complexity.

*   **File Name:** `tutorials/UAT_AND_TUTORIAL.py`
*   **Content & Flow:** This solitary file will orchestrate the entire user journey outlined in the UAT scenarios. It will sequentially guide the user through the following distinct phases:
    1.  **Initialisation:** Setting up the system configuration, loading environment variables, and establishing the mock/real execution context.
    2.  **Ingestion Simulation:** Programmatically simulating the upload of the `testfiles/test_text.txt` artifact into the system pipeline.
    3.  **Processing Execution:** Triggering the semantic chunking engine and demonstrating the step-by-step construction of the RAPTOR tree in memory.
    4.  **Interactive Engagement:** Pausing execution to prompt the user (within the notebook interface) to answer a simulated AI question, demonstrating the unlocking mechanism of a specific `GraphNode`.
    5.  **Restructuring:** Executing the Pivot KJ analysis logic, showcasing how the internal node references are dynamically remapped based on a selected axis.
    6.  **Artifact Generation:** Concluding the tutorial by displaying the final, generated Markdown text and rendering the corresponding Mermaid.js diagram directly within the notebook's output cell.

## 5. Tutorial Validation

The validation process for this tutorial is straightforward and deterministic. A developer or QA engineer must execute the command `uv run marimo edit tutorials/UAT_AND_TUTORIAL.py` (or run it headlessly as a standard script). The validation is considered successful only if all of the following conditions are met:
1.  **Error-Free Execution:** The script must run from the first cell to the last without raising any unhandled Python exceptions or halting unexpectedly.
2.  **State Integrity:** Whether operating in Mock Mode or Real Mode, the simulated responses must successfully trigger the correct state changes within the underlying Pydantic domain models (e.g., correctly toggling the `is_unlocked` boolean on a node).
3.  **Visual Proof:** The final output cell of the notebook must clearly and accurately demonstrate the transformation of the unstructured input text into a highly structured, multi-dimensional format, culminating in the display of the generated requirements document and the Mermaid UML diagram.
