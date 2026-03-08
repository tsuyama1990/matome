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
**Expected Result:** The user feels relief from the cognitive load of reading the raw text and experiences the excitement of instantly generating a structured system design from an unstructured manual.

### Scenario ID: UAT-02 - Multi-Dimensional Analysis for a Consultant (Advanced)
**Description:** A business consultant needs to synthesise multiple market reports to find a unique angle for a strategy pitch.
**Steps:**
1.  **Ingestion:** The user uploads three separate documents detailing market trends, competitor analysis, and regulatory changes.
2.  **Exploration:** The user navigates the massive combined knowledge tree using the Semantic Zoom UI, never losing their place thanks to the minimap and breadcrumbs.
3.  **Restructuring (Pivot KJ):** The user defines a custom axis: "Opportunities vs Threats in the European Market." The system pulls data across all three documents and physically reorganises the nodes into a custom matrix on the canvas.
4.  **Web-Grounding:** The AI flags a "Threat" node regarding a specific law and suggests, "Recent news indicates this law's enforcement has been delayed. Would you like to downgrade this threat?" The user accepts the suggestion.
**Expected Result:** The consultant successfully breaks out of the original authors' narrative structures, generating a completely novel and externally validated insight matrix without manual copy-pasting.

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
