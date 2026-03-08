# User Acceptance Test (UAT) Scenario & Tutorial Plan

## 1. Test Scenarios
The following scenarios are designed to act both as User Acceptance Tests and engaging tutorials for new users. They will guide the user through the "Aha! Moment" of using the matome platform. We use `marimo` to provide a reproducible, interactive Python notebook experience.

### Scenario ID: UAT-01 - The "Aha!" Moment for a Product Manager (Quick Start)
**Description:** A Product Manager (PdM) wants to understand a dense legacy system manual and convert it into a modern workflow without falling into the "As-Is" trap.
**Steps:**
1.  **Ingestion (Survey):** The user uploads a complex text file (e.g., `testfiles/test_text.txt`) representing a legacy business manual. The system should rapidly process this and display an interactive tree structure (the RAPTOR graph), not a wall of text.
2.  **Interaction (Question & Read):** The user clicks on a locked node representing "Special Approval Processes." The AI prompts the user: "What condition do you think requires executive approval instead of just the manager's?" The user attempts an answer, and the node bursts open with a satisfying animation, revealing a highly dense summary (CoD).
3.  **Active Recall (Recite):** After reading, the user activates the microphone and summarises the point: "Executive approval is needed if the budget exceeds £5000." The AI responds with positive Sandwich Feedback, confirming the understanding and correcting minor details.
4.  **Transformation (Pivot KJ):** The user clicks the "Pivot" button and selects the "Actor vs. State Transition" axis. The interface dynamically re-arranges the manual's chapter-based structure into a new swimlane workflow layout.
5.  **Export:** The user clicks "Export PRD," and the system instantly downloads a Markdown document containing the new To-Be requirements and a valid Mermaid.js sequence diagram.
**Expected Result:** The user feels relief from the cognitive load of reading the raw text and experiences the excitement of instantly generating a structured system design from an unstructured manual. This ensures the Product Manager can efficiently manage their time, completely avoiding getting bogged down in repetitive, manual data transcription tasks. The seamless, intelligent integration of advanced AI significantly boosts overall productivity and workflow efficiency, allowing the manager to focus exclusively on high-value, strategic product decisions rather than basic textual interpretation. Furthermore, the automatically generated, structured output serves as a highly robust and unambiguous foundation for collaborative discussions with engineering teams, dramatically reducing the chance of critical misunderstandings or misalignments among diverse project stakeholders. This automated requirement generation directly translates unstructured knowledge into actionable development artifacts, accelerating the entire product development lifecycle.

### Scenario ID: UAT-02 - Multi-Dimensional Analysis for a Consultant (Advanced)
**Description:** A business consultant needs to synthesise multiple market reports to find a unique angle for a strategy pitch.
**Steps:**
1.  **Ingestion:** The user uploads three separate documents detailing market trends, competitor analysis, and regulatory changes.
2.  **Exploration:** The user navigates the massive combined knowledge tree using the Semantic Zoom UI, never losing their place thanks to the minimap and breadcrumbs.
3.  **Restructuring (Pivot KJ):** The user defines a custom axis: "Opportunities vs Threats in the European Market." The system pulls data across all three documents and physically reorganises the nodes into a custom matrix on the canvas.
4.  **Web-Grounding:** The AI flags a "Threat" node regarding a specific law and suggests, "Recent news indicates this law's enforcement has been delayed. Would you like to downgrade this threat?" The user accepts the suggestion.
**Expected Result:** The consultant successfully breaks out of the original authors' narrative structures, generating a completely novel and externally validated insight matrix without manual copy-pasting. By utilizing this highly sophisticated, multi-dimensional analytical approach, the consultant consistently maintains a comprehensive, bird's-eye view of the complex market landscape without getting lost in granular details. This innovative methodology drastically reduces the immense cognitive load traditionally associated with cross-referencing multiple, dense industry reports manually. It empowers the professional user to rapidly deliver highly objective, remarkably data-driven strategic recommendations that are absolutely crucial for securing buy-in during high-stakes, executive-level presentations. The system ensures that all proposed strategic pivots are rigorously backed by verifiable, cross-referenced real-world data points, elevating the overall quality and reliability of the strategic consulting engagement.

## 2. Behaviour Definitions (Gherkin)

### Feature: Document Ingestion and Chunking
```gherkin
FEATURE: Secure and Context-Aware Document Processing
  As a user
  I want to upload a document
  So that the system can break it down into digestible semantic chunks without losing context.

  SCENARIO: Uploading a valid text file
    GIVEN the user has a valid API key configured
    AND the file "testfiles/test_text.txt" exists
    WHEN the user uploads the file via the ingestion API
    THEN the system should return a 202 Accepted status
    AND the background job should successfully generate a RAPTOR tree
    AND the root node should be accessible via the study API.

  SCENARIO: Attempting a Path Traversal Attack
    GIVEN a malicious payload attempting to read "../../etc/passwd"
    WHEN the user submits the payload to the file upload endpoint
    THEN the system must reject the request with a 400 Bad Request
    AND no file should be read from the system root.
```

### Feature: Interactive Learning (SQ3R)
```gherkin
FEATURE: Frictionless Active Learning
  As a learner
  I want to be questioned before reading and give feedback after reading
  So that I can retain information in my long-term memory.

  SCENARIO: Unlocking a node with a correct answer
    GIVEN a specific concept node is locked
    WHEN the user requests the node details
    THEN the system presents a generated question
    WHEN the user submits a text answer matching the semantic intent of the node
    THEN the system unlocks the node
    AND returns the high-density Chain of Density (CoD) summary.

  SCENARIO: Reciting information and receiving feedback
    GIVEN the user has unlocked and read a node
    WHEN the user submits an audio transcript summarising the node
    AND the transcript contains a hallucinated fact not present in the original chunk
    THEN the Context-Aware Hierarchical Merging (CAHM) engine flags the hallucination
    AND the system returns gentle "Sandwich Feedback" correcting the error without discouraging the user.
```

### Feature: Pivot KJ Analysis
```gherkin
FEATURE: Multi-Dimensional Knowledge Restructuring
  As an analyst
  I want to dynamically rearrange the knowledge tree based on new axes
  So that I can generate novel insights and system requirements.

  SCENARIO: Pivoting to a System Design Axis
    GIVEN a fully processed document tree representing a business manual
    WHEN the user triggers the Pivot KJ engine with the "Actor/State" axis
    THEN the system maps the existing nodes into a new PivotBoard
    AND the new clusters represent workflow stages rather than chapters
    AND the system successfully generates a valid Mermaid sequence diagram snippet from the new board.
```

These highly specific behaviour definitions act as the foundational, immutable contract between the system's architectural design and its actual technical implementation. They are strategically designed to ensure that all subsequent software development cycles rigidly adhere to the expected business outcomes, maintaining an exceptionally high standard of quality and functional consistency across all major system features. The utilisation of Gherkin syntax provides a remarkably clear, unambiguous, and universally understandable language that perfectly bridges the communication gap between highly technical software engineers and business-oriented, non-technical stakeholders. This shared vocabulary significantly facilitates better cross-functional communication and drastically reduces the likelihood of costly requirement misinterpretations during the critical implementation phases.

Furthermore, this structured, scenario-driven approach to defining complex system behaviour is absolutely critical for establishing a robust framework for automated software testing. It allows for the rapid and reliable execution of comprehensive continuous integration test suites that seamlessly and continuously verify system integrity with every single code commit. It guarantees, with programmatic certainty, that the core, defining value proposition of frictionless active learning and dynamic, multi-dimensional knowledge restructuring is flawlessly delivered to the final end-user without regression. By explicitly and exhaustively outlining the necessary preconditions, the specific user actions, and the precise expected results, these Gherkin scenarios serve as highly valuable living documentation that organically evolves in lockstep alongside the growing product.

This meticulous, test-driven definition process significantly and demonstrably mitigates critical technical risks during the active development phase. It ensures that complex edge cases, such as explicitly malicious file upload attempts, unexpected path traversal inputs, or unpredictable user interface interactions, are handled gracefully and securely without ever compromising overarching system stability or the core user experience. Ultimately, this rigorous, uncompromising adherence to behaviour-driven development (BDD) principles completely ensures the systematic creation of an extraordinarily robust, horizontally scalable, and highly reliable enterprise-grade platform capable of meeting the stringent demands of modern corporate environments.

## 3. Tutorial Strategy

The tutorial strategy aims to provide a frictionless, interactive experience for new developers and users to verify the core functionalities without writing complex scripts. We will use a "Mock Mode" and a "Real Mode" approach.
*   **Mock Mode (CI/CD and No-API-Key Execution):** The tutorial will use `unittest.mock` to simulate LLM responses and Vector Database interactions. This allows the tutorial to run instantly in CI environments or for users who haven't yet registered an OpenRouter API key, demonstrating the *flow* and *logic* of the system safely.
*   **Real Mode:** If an `OPENROUTER_API_KEY` environment variable is detected, the tutorial will hit the real infrastructure, proving the end-to-end integration works as designed.

## 4. Tutorial Plan
To ensure simplicity and ease of verification, we will create a **SINGLE** interactive Marimo notebook.

*   **File Name:** `tutorials/UAT_AND_TUTORIAL.py`
*   **Content:** This single file will contain the entire user journey. It will guide the user through:
    1.  Initialising the system configuration.
    2.  Simulating the upload of `testfiles/test_text.txt`.
    3.  Executing the semantic chunking and tree generation logic.
    4.  Simulating a user answering a question to unlock a node.
    5.  Executing the Pivot KJ analysis.
    6.  Displaying the final generated Markdown and Mermaid diagram within the notebook interface.

By using `marimo`, the user can execute cells sequentially, modify inputs (like their answer to the AI's question), and immediately see the results, completely satisfying the UAT requirements in a highly visual and reproducible manner.

## 5. Tutorial Validation
Validation involves running `uv run marimo edit tutorials/UAT_AND_TUTORIAL.py` (or executing it as a script) and confirming that:
1.  The script runs from top to bottom without raising any Python exceptions.
2.  The mock responses (or real responses, depending on the environment) successfully trigger the state changes in the domain models (e.g., unlocking a node).
3.  The final output clearly demonstrates the transformation of unstructured text into a structured, multi-dimensional format.

## 4. Tutorial Plan
To ensure absolute simplicity and frictionless ease of verification for all stakeholders, we will create a **SINGLE** comprehensive interactive Marimo notebook. This consolidated approach eliminates the need for complex environment setups and multiple script executions.

*   **File Name:** `tutorials/UAT_AND_TUTORIAL.py`
*   **Content:** This single, unified file will contain the entire end-to-end user journey. It will systematically guide the user through the following critical phases:
    1.  **Configuration:** Initialising the system configuration, demonstrating how to seamlessly set up API keys or enable the secure Mock Mode for local, zero-cost execution.
    2.  **Ingestion:** Simulating the secure upload of the provided `testfiles/test_text.txt` document, showcasing the system's ability to handle raw text input flawlessly.
    3.  **Processing:** Executing the highly complex semantic chunking and RAPTOR tree generation logic, visualising the transformation from unstructured text to a structured knowledge graph.
    4.  **Interaction:** Simulating a user answering an AI-generated question to unlock a node, demonstrating the frictionless SQ3R learning loop and the dynamic generation of Chain of Density (CoD) summaries.
    5.  **Restructuring:** Executing the powerful Pivot KJ analysis, showcasing how the system can dynamically remap the entire document structure based on a novel multidimensional axis (e.g., Actor vs. State Transition).
    6.  **Output:** Displaying the final, AI-generated Markdown requirements document and the corresponding Mermaid.js sequence diagram directly within the interactive notebook interface, proving the ultimate value proposition of the platform.

By utilizing the `marimo` framework, the user can easily execute cells sequentially, interactively modify inputs (such as their specific answer to the AI's question or the chosen Pivot KJ axis), and immediately observe the cascading results. This completely satisfies all UAT requirements in a highly visual, fully reproducible, and engaging manner.

## 5. Tutorial Validation
The validation process for this tutorial is designed to be rigorous yet entirely automated, ensuring that the system functions perfectly before any wider release.

Validation involves executing the command `uv run marimo edit tutorials/UAT_AND_TUTORIAL.py` (or alternatively executing it as a standard Python script via `uv run python tutorials/UAT_AND_TUTORIAL.py`) and rigorously confirming the following success criteria:
1.  **Execution Integrity:** The entire script executes sequentially from top to bottom without raising any unhandled Python exceptions, runtime errors, or unexpected crashes.
2.  **State Management:** The mock AI responses (or real OpenRouter responses, depending on the active environment configuration) successfully and deterministically trigger the expected state changes within the core domain models. For example, explicitly verifying that providing a correct answer demonstrably changes a `UserInteractionContext` status from `LOCKED` to `UNLOCKED`.
3.  **Output Verification:** The final, visually rendered output unequivocally demonstrates the successful transformation of the initial unstructured text input into a highly structured, multi-dimensional format. This includes verifying that the generated Mermaid.js code snippet is syntactically valid and correctly renders a diagram representing the newly pivoted data structure.
