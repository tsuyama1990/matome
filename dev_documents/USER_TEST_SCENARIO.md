# User Acceptance Test (UAT) Scenario & Tutorial Plan

## 1. Test Scenarios

### Scenario ID: UAT-01 - The "Aha!" Moment for a Product Manager (Quick Start)
**Priority: High**
**Description:** A Product Manager (PdM) is tasked with modernizing a sprawling, outdated legacy system manual. Their goal is to convert this unstructured block of text into a modern workflow. However, they need to avoid the "As-Is" trap—simply digitizing inefficient existing processes without any structural improvement. This test scenario ensures the matome system effortlessly ingests the text, automatically maps out a visually appealing knowledge tree, and actively tests the user's comprehension before allowing them to restructure the manual into a completely new sequence diagram. This provides an immediate "Aha!" moment where cognitive load is visibly reduced and genuine insight is gained.
**Steps:**
1.  **Ingestion (Survey):** The user begins the session by uploading a complex text file (e.g., `testfiles/test_text.txt`) representing a dense legacy business manual. The system must rapidly process this file securely in the background, normalize the text by removing extraneous noise, and display an interactive hierarchical tree structure (the RAPTOR graph), completely avoiding presenting a wall of text.
2.  **Interaction (Question & Read):** The user clicks on a visibly locked node representing "Special Approval Processes." Instead of immediately showing the text, the AI prompts the user: "What condition do you think requires executive approval instead of just the manager's based on the surrounding context?" The user thinks critically and attempts an answer. The node bursts open with a satisfying visual animation, revealing a highly dense summary (Chain of Density).
3.  **Active Recall (Recite):** After reading the dense summary, the user activates the microphone and summarises the point: "Executive approval is strictly needed if the budget exceeds £5000." The AI processes this, responds with positive Sandwich Feedback, confirming the understanding, and corrects minor details.
4.  **Transformation (Pivot KJ):** The user clicks the "Pivot" button on the interface and selects the "Actor vs. State Transition" axis. The system's interface dynamically re-arranges the manual's original chapter-based structure into an entirely new swimlane workflow layout.
5.  **Export:** Finally, the user clicks the "Export PRD" button. The system instantly downloads a Markdown document containing the newly derived To-Be requirements alongside a valid, immediately usable Mermaid.js sequence diagram.
**Expected Result:** The user feels immediate relief from the heavy cognitive load of reading raw text. They experience the excitement of interacting with the material and instantly generating a structured system design from an unstructured, tedious manual.

### Scenario ID: UAT-02 - Multi-Dimensional Analysis for a Consultant (Advanced)
**Priority: Medium**
**Description:** A business consultant needs to rapidly synthesize multiple, distinct market reports to find a unique, actionable angle for an urgent strategy pitch to executive management. This scenario verifies the system's capacity to handle multiple disparate documents, merge them into a single coherent knowledge graph, and most importantly, allow the user to execute a completely custom Multi-Dimensional Semantic KJ (Pivot KJ) operation to reveal hidden cross-sectional relationships. This tests the system's ability to act as a powerful sounding board.
**Steps:**
1.  **Ingestion:** The user uploads three entirely separate, complex documents detailing specific market trends, a rigorous competitor analysis, and highly detailed regulatory changes. The system ingests these concurrently and maps them into the vector database.
2.  **Exploration:** The user fluidly navigates the massive combined knowledge tree using the Semantic Zoom UI. As they zoom into specific nodes, unrelated branches fade out. The user never loses their structural place thanks to the persistent minimap and dynamic breadcrumb trail actively tracking their depth.
3.  **Restructuring (Pivot KJ):** The user defines a totally custom analytical axis: "Immediate Opportunities vs Long-Term Threats in the European Market." The system's backend KnowledgeGraphService pulls semantically relevant data across all three disparate documents and physically reorganizes the nodes into a newly formed custom matrix on the central canvas, completely disregarding the authors' original document structures.
4.  **Web-Grounding (Optional Suggestion):** The AI flags a "Threat" node regarding a specific upcoming law and provides an interactive suggestion, "Recent news indicates this law's enforcement has been delayed for two years. Would you like to downgrade this threat's severity?" The user reviews the source link and accepts the suggestion, structurally updating the board.
**Expected Result:** The consultant successfully breaks out of the original authors' constrained narrative structures. They generate a completely novel, externally validated insight matrix effortlessly, proving the system's value for high-level knowledge workers.

## 2. Behaviour Definitions (Gherkin)

### Feature: Document Ingestion, Normalization, and Chunking
```gherkin
FEATURE: Secure, Resilient, and Context-Aware Document Processing
  As a professional user seeking to synthesize knowledge
  I want to securely upload a massive text document
  So that the system can automatically break it down into digestible semantic chunks without losing context or exposing vulnerabilities.

  SCENARIO: Uploading a valid, structured text file
    GIVEN the user has successfully configured a valid system API key in the environment configuration
    AND the targeted source file "testfiles/test_text.txt" exists and contains valid utf-8 encoded text
    WHEN the user uploads the file via the secure ingestion API endpoint
    THEN the system should immediately return a 202 Accepted status code indicating background processing has started
    AND the background job should successfully generate a RAPTOR hierarchical tree utilizing semantic similarity algorithms
    AND the root node of the constructed tree should be fully accessible via the study API for user interaction.

  SCENARIO: Attempting a malicious Path Traversal Attack
    GIVEN a malicious payload attempting to read sensitive system files via "../../etc/passwd" or similar tactics
    WHEN the malicious user submits this manipulated payload to the file upload endpoint
    THEN the backend system must explicitly reject the request by canonicalizing the path and throwing a validation error
    AND the API should return a 400 Bad Request status code
    AND absolutely no file should be read from or exposed from the underlying system root.

  SCENARIO: Processing a document with excessive noise
    GIVEN a document containing numerous repeated headers, footers, and page numbers
    WHEN the document is processed by the DocumentProcessingService
    THEN the IngestionEngine should successfully identify and scrub the extraneous noise
    AND the resulting semantic chunks should only contain the core proposition-level text.
```

### Feature: Frictionless Interactive Learning (SQ3R Mechanics)
```gherkin
FEATURE: Gamified and Frictionless Active Learning Loop
  As a dedicated learner studying dense material
  I want to be proactively questioned before reading and actively give feedback after reading
  So that I can trigger generative learning, bypass the forgetting curve, and retain information deeply in my long-term memory.

  SCENARIO: Successfully unlocking a node with a correct conceptual answer
    GIVEN a specific, high-level concept node is currently in a visually locked state on the UI canvas
    WHEN the user requests to view the node's underlying details
    THEN the active learning system intercepts the request and presents a dynamically generated reasoning question
    WHEN the user submits a text answer that strictly matches the semantic intent of the node's underlying summary
    THEN the system evaluates the answer favorably and permanently unlocks the node
    AND returns the high-density Chain of Density (CoD) summary alongside visual reward feedback.

  SCENARIO: Reciting information verbally and receiving corrective feedback
    GIVEN the user has successfully unlocked and thoroughly read a node's high-density summary
    WHEN the user submits an audio transcript (or simulated text equivalent) attempting to summarize the node's key points
    AND the transcript inadvertently contains a hallucinated fact or numerical error not present in the original semantic chunk
    THEN the Active Learning engine flags the semantic discrepancy
    AND the system returns gentle "Sandwich Feedback" (praise, correction, encouragement) correcting the specific error without discouraging the user's progress.
```

### Feature: Pivot KJ Multi-Dimensional Analysis
```gherkin
FEATURE: Dynamic Multi-Dimensional Knowledge Restructuring
  As an advanced system architect or business analyst
  I want to dynamically rearrange the generated knowledge tree based on entirely new analytical axes
  So that I can synthesize novel insights, break status quo bias, and instantly generate system requirements or strategic plans.

  SCENARIO: Pivoting an unstructured manual to a rigorous System Design Axis
    GIVEN a fully processed document tree representing a legacy, unstructured business manual
    WHEN the user triggers the Pivot KJ engine and selects the "Actor vs State Transition" axis
    THEN the KnowledgeGraphService maps the existing nodes into a completely new PivotBoard data model
    AND the new visual clusters represent linear workflow stages rather than the original document's chapters
    AND the system successfully generates a logically valid Mermaid sequence diagram snippet derived strictly from the newly arranged board.
```

## 3. Tutorial Strategy

The tutorial strategy is designed to provide a frictionless, highly interactive, and immediately gratifying experience for new developers, architects, and users. The goal is to allow them to visually verify the core architectural requirements and functionalities without writing complex scripts or battling environment setups. We achieve this by utilizing an interactive Marimo notebook, providing both a "Mock Mode" and a "Real Mode" approach.

*   **Mock Mode (CI/CD and Rapid Local Execution):** The tutorial will intelligently utilize Python's `unittest.mock` framework to simulate responses from external Large Language Models (LLMs) and Vector Database interactions. This "Mock Mode" is critical. It allows the tutorial to run instantaneously in continuous integration (CI) environments or for users who simply want to test the domain logic locally without having registered a paid OpenRouter API key. It safely demonstrates the exact workflow, state transitions, and business logic of the system.
*   **Real Mode (End-to-End Verification):** If a valid `OPENROUTER_API_KEY` environment variable is successfully detected within the strict `CredentialConfig` boundaries, the tutorial will seamlessly switch to hitting the real, live infrastructure. This proves that the external adapter protocols, API routing, and actual AI inference pipelines function precisely as architected end-to-end.

## 4. Tutorial Plan

To guarantee absolute simplicity and ease of verification, we will consolidate the entire learning and testing journey into a single, executable file. Managing multiple tutorial files increases cognitive overhead for a new user, contradicting our system's core philosophy. Therefore, we mandate a **SINGLE** interactive Marimo notebook.

*   **File Name:** The file MUST be strictly named `tutorials/UAT_AND_TUTORIAL.py`.
*   **Content and Flow:** This unified notebook will guide the user sequentially through the complete system lifecycle:
    1.  **System Initialization:** Demonstrating how to securely load the `PipelineConfig` and initialize the `ProductionDIContainer`.
    2.  **Document Ingestion:** Simulating the secure upload and parsing of the `testfiles/test_text.txt` sample file.
    3.  **Semantic Processing:** Executing the semantic chunking algorithm and visually displaying the initial hierarchical RAPTOR tree structure.
    4.  **Active Learning Loop:** Simulating the user interaction flow—the AI presenting a question, the user (or mock) providing an answer, the node unlocking, and the high-density summary being revealed.
    5.  **Insight Generation:** Executing the Pivot KJ analysis, structurally reorganizing the nodes based on a predefined axis (e.g., "Workflow Sequence").
    6.  **Final Export:** Displaying the final generated Markdown requirements and successfully rendering the resulting Mermaid diagram directly within the notebook interface.

By utilizing `marimo`, the user is empowered to execute individual cells sequentially, dynamically modify inputs (such as their simulated answer to the AI's question), and immediately observe the state changes and results. This completely satisfies all high-level UAT requirements in a highly visual, deeply reproducible manner.

## 5. Tutorial Validation

Validation of this tutorial system is straightforward and robust. It involves running `uv run marimo edit tutorials/UAT_AND_TUTORIAL.py` (or executing it standardly as a script using `uv run python tutorials/UAT_AND_TUTORIAL.py` with the appropriate PYTHONPATH). The validation is considered successful if and only if:
1.  The Marimo notebook script executes from top to bottom perfectly without raising any uncaught Python exceptions, TypeErrors, or ValidationErrors from the core Pydantic domain models.
2.  The mock responses (or real external API responses, depending on the active environment configuration) successfully and deterministically trigger the expected state changes within the application's domain models (e.g., successfully transitioning a `KnowledgeNode` from a 'Locked' to an 'Unlocked' state).
3.  The final output clearly, visually, and structurally demonstrates the successful transformation of the unstructured input text into a highly structured, multi-dimensional format, culminating in a valid Mermaid diagram representation.
