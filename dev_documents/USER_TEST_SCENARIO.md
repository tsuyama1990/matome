# User Acceptance Test (UAT) Scenario & Tutorial Plan


## 1. Test Scenarios

### Scenario ID: UAT-01 - The "Aha!" Moment for a Product Manager (Quick Start)
**Priority:** High
**Description:** A Product Manager (PdM) wants to understand a dense legacy system manual and convert it into a modern workflow without falling into the "As-Is" trap. This scenario serves as the primary gateway for new users to experience the immediate value of the matome platform. The overarching goal is to practically demonstrate how effectively the system handles extremely long, unstructured texts. By breaking them down into precise semantic chunks and presenting a visual hierarchy, the system completely bypasses traditional cognitive overload. The user will experience the core SQ3R loop in its entirety: Surveying the generated RAPTOR tree, answering a contextual Question to unlock a node, Reading the high-density summary, and Reciting the knowledge back to the AI. Finally, the user will actively leverage the MD-SKJ engine to pivot the document structure and export actionable system design artifacts (Mermaid sequence diagrams).

**Steps:**
1. **Ingestion (Survey):** The user begins by uploading a complex text file (e.g., `testfiles/test_text.txt`) that represents a dense, analogue legacy business manual (e.g., a massive 50-page PDF detailing procurement rules). The backend pipeline automatically initiates, chunking the text via semantic analysis (cosine similarity of embeddings), embedding the chunks into the vector store, and mathematically constructing the hierarchical RAPTOR tree using UMAP and GMM. The React frontend rapidly displays this interactive tree structure, rather than a linear wall of text, achieving the initial "Semantic Zooming" objective with sub-second rendering.
2. **Interaction (Question & Read):** The user visually navigates the tree, noting the overall structure, and clicks on a specific locked node representing "Special Executive Approval Processes." Instantly, the AI prompts the user: "Based on the surrounding context, what condition do you think requires executive approval instead of just the line manager's?" The user contemplates the structure and attempts an answer (e.g., typing "high budget"). Upon submission, the node bursts open with a satisfying visual animation, revealing a highly dense Chain of Density (CoD) summary that explicitly defines the £5000 threshold.
3. **Active Recall (Recite):** After thoroughly reading the newly revealed node content, the user activates the microphone (or text input) and summarises the core point in their own words: "Executive approval is strictly needed if the total requested budget exceeds £5000." The AI processes this input, compares it against the node's vector embedding, and responds with positive "Sandwich Feedback," confirming their understanding and gently correcting any minor details, thereby solidifying the knowledge in long-term memory.
4. **Transformation (Pivot KJ):** Having grasped the individual nodes and the overall narrative, the user clicks the "Pivot" button on the canvas and selects the "Actor vs. State Transition" axis from the dropdown menu. The backend MD-SKJ engine dynamically re-arranges the manual's original chapter-based structure, querying the vector database for metadata tags, into a completely new swimlane workflow layout on the screen, visually separating actions by "Employee," "Manager," and "Executive."
5. **Export:** Satisfied with the new, highly logical To-Be structure, the user clicks "Export PRD." The system instantly generates and downloads a Markdown document containing the new To-Be requirements alongside a syntactically valid Mermaid.js sequence diagram, perfectly formatted and ready to be pasted directly into Jira or Confluence for the development team.
**Expected Result:** The user feels immediate relief from the immense cognitive load typically associated with reading raw legacy text. They experience the excitement and empowerment of instantly generating a structured, modern, actionable system design from an unstructured, outdated manual, successfully completing the primary user journey and validating the core product hypothesis.

### Scenario ID: UAT-02 - Multi-Dimensional Analysis for a Consultant (Advanced)
**Priority:** Medium
**Description:** A business consultant needs to synthesise multiple disparate market reports to find a unique, unconsidered angle for a strategic pitch to a corporate management board. This advanced scenario demonstrates the platform's advanced capability to act not merely as an intelligent reader, but as a powerful, multi-document cross-analysis engine. The primary focus here is proving the profound efficacy of the MD-SKJ engine when applied to a vast, highly heterogeneous dataset. The consultant is searching for hidden connections, structural risks, and emerging opportunities that are completely invisible when reading the documents in isolated sequence. The system must definitively prove it can break down the original authors' narrative biases, extract the underlying facts, and present a purely objective, multi-dimensional view of the combined data landscape.

**Steps:**
1. **Bulk Ingestion:** The user uploads three separate, lengthy documents simultaneously: a report detailing macro-economic market trends, a technical competitor analysis, and a legal brief on upcoming regulatory changes. The system ingests all three, running the RAPTOR tree generation process concurrently for each, and then mathematically merges them into a massive, unified knowledge graph representing the entire business domain.
2. **Exploration and Navigation:** The user navigates the massive combined knowledge tree using the Semantic Zoom UI. Despite the overwhelming volume of information (potentially tens of thousands of tokens), they never lose their spatial orientation thanks to the spatial context maintenance features, specifically the interactive radar minimap and the dynamic, clickable breadcrumb trails that constantly ground them in the data hierarchy.
3. **Restructuring (Pivot KJ Matrix):** The user defines a custom analytical axis in the UI: "Opportunities vs Threats in the European Market." The system executes a complex hybrid search against the vector database, pulling relevant semantic chunks across all three disparate documents using both dense vector similarity and sparse metadata filtering (e.g., tags for `region: EU`), and physically reorganises the nodes into a custom visual matrix on the canvas. The original document boundaries and chapters are completely and seamlessly dissolved.
4. **Web-Grounding and Bias Correction:** The LangGraph AI orchestrator actively analyses the newly formed spatial clusters. It flags a specific "Threat" node regarding a new environmental law extracted from the legal brief and suggests via a non-intrusive pop-up: "Recent news indicates this law's enforcement has been officially delayed by two years. Would you like to downgrade this threat's severity in your matrix?" The user reviews the AI's cited external source and accepts the suggestion, adjusting the visual layout and node weighting accordingly.
5. **Strategic Export:** The user exports the finalised, externally validated custom matrix. The system generates a comprehensive Executive Summary Markdown document, explicitly highlighting the newly discovered cross-document insights and the specific actionable business strategies derived directly from the newly constructed multi-dimensional spatial view.
**Expected Result:** The consultant successfully breaks completely out of the original authors' constrained narrative structures. They generate a completely novel, externally validated, and highly defensible insight matrix without resorting to any manual copy-pasting, highlighter pens, or laborious manual cross-referencing between PDFs. The platform acts as an intelligent, objective sounding board, proving its immense, time-saving value in high-stakes strategic business analysis.



## 2. Behavior Definitions

The following behaviour definitions are written in standard Gherkin syntax (GIVEN/WHEN/THEN). They serve as the strict, unambiguous foundation for both our automated testing suite (via pytest-bdd or similar frameworks) and our shared understanding of the absolute system boundaries. These scenarios explicitly map the abstract architectural requirements to concrete, verifiable backend and frontend states, ensuring that all developers understand exactly what constitutes a "working" feature.

### Feature: Document Ingestion and Chunking
```gherkin
FEATURE: Secure and Context-Aware Document Processing
  As a registered user
  I want to upload a massive, unstructured document
  So that the backend system can break it down into highly digestible semantic chunks without losing the original narrative context.

  SCENARIO: Uploading a valid text file successfully initiates asynchronous processing
    GIVEN the user has a valid API key configured in their active session
    AND the local file "testfiles/test_text.txt" exists, is readable, and is under the 50MB file size limit
    WHEN the user uploads the file via a POST request to the primary `/api/v1/ingest` endpoint
    THEN the API must immediately return a 202 Accepted HTTP status code
    AND the background LangGraph job must successfully enqueue and begin generating a RAPTOR tree
    AND upon completion, the root node of that tree must be fully accessible via a GET request to the `/api/v1/study/{doc_id}` API for UI rendering.

  SCENARIO: Attempting a Path Traversal Attack is aggressively blocked
    GIVEN a malicious actor crafts a payload attempting to read the system file "../../etc/passwd"
    WHEN the user submits the malicious payload as the `filename` parameter to the file upload endpoint
    THEN the system must instantly reject the request with a 400 Bad Request HTTP status code
    AND the security middleware must mathematically ensure no file descriptor is ever opened on the operating system root
    AND the attempt must be safely logged in the audit trail without exposing internal server absolute paths.
```

### Feature: Interactive Learning (SQ3R)
```gherkin
FEATURE: Frictionless Active Learning Loop
  As a learner visually navigating the knowledge graph
  I want to be questioned before reading a node and give summary feedback after reading it
  So that I can effectively retain complex, highly technical information in my long-term memory.

  SCENARIO: Unlocking a node with a semantically correct answer
    GIVEN a specific, high-level concept node on the React canvas is currently rendered in a "locked" (blurred) state
    WHEN the user clicks the node, requesting to expand the details
    THEN the backend system generates and presents an AI-generated question based strictly on the node's hidden Chain of Density summary
    WHEN the user submits a text answer via the UI that semantically matches the core intent of the hidden summary (verified via vector cosine similarity > 0.85)
    THEN the system updates the node state to unlocked
    AND returns the high-density summary payload for the frontend to render the expansion animation.

  SCENARIO: Reciting information and receiving constructive sandwich feedback
    GIVEN the user has successfully unlocked and read the full text of a specific node
    WHEN the user submits an audio transcript or text summarising the node's core concept via the Recite feature
    AND the user's transcript explicitly contains a hallucinated fact or numerical error not present in the original semantic chunk
    THEN the Context-Aware AI engine must accurately flag the specific hallucinated entity
    AND the system must return gentle "Sandwich Feedback" (Praise for effort, Correction of the error, Praise for overall structure) correcting the error without discouraging the user's continued learning.
```

### Feature: Pivot KJ Analysis
```gherkin
FEATURE: Multi-Dimensional Knowledge Restructuring
  As a systems analyst or senior business consultant
  I want to dynamically rearrange the entire knowledge tree based on entirely new, orthogonal axes
  So that I can generate completely novel insights and highly structured system requirements from unstructured data.

  SCENARIO: Pivoting to a System Design Workflow Axis
    GIVEN a fully processed, persisted document tree representing a linear, narrative business manual
    WHEN the user triggers the Pivot KJ engine via the UI, explicitly selecting the predefined "Actor vs State Transition" axis
    THEN the backend system must query the vector database using hybrid metadata filtering to retrieve relevant chunks
    AND map the existing nodes into a new spatial layout payload
    AND the new visual clusters must definitively represent workflow stages (e.g., "Approval", "Rejection") rather than the original document chapters
    AND the system must successfully generate a valid Mermaid.js sequence diagram snippet derived strictly and exclusively from the newly established visual board relationships.
```

These definitions strictly dictate the precise operational boundaries of our system. They ensure that engineering effort is not wasted on building extraneous, out-of-scope features, but strictly fulfills the precise promises made in the architectural design document. Every pull request submitted must conclusively demonstrate via automated tests that it does not break or alter these core behavioral contracts. By heavily formalizing these behaviors, we completely bridge the gap between human language product requirements and executable, deterministic code tests.



## 3. Tutorial Strategy

The tutorial strategy is meticulously designed to provide a frictionless, interactive, and highly visual experience for new developers, external auditors, and initial users. Our primary objective is to allow anyone to instantly verify the core functionalities and experience the platform's "Aha!" moment without needing to write complex, boilerplate Python scripts or configure extensive local database environments. To achieve this immediate validation, we employ a dual-mode execution strategy wrapped entirely within an interactive notebook environment.

*   **Mock Mode (CI/CD and No-API-Key Execution):** The tutorial script will intelligently default to a "Mock Mode" if a valid external API key is absent from the environment. In this mode, the notebook utilizes functional, deterministic Python replacements (strictly avoiding brittle, complex mock frameworks like `unittest.mock`) to simulate LLM network responses and Vector Database persistence. This guarantees that the tutorial can run instantly and flawlessly in Continuous Integration (CI) environments or for users who are merely evaluating the platform's logical flow. It safely and rapidly demonstrates the Pydantic data transformations, the LangGraph state transitions, and the core algorithmic logic of the system.
*   **Real Mode:** If an `OPENROUTER_API_KEY` (or equivalent valid configuration) is explicitly detected in the environment variables, the tutorial will seamlessly and automatically switch to "Real Mode." It will execute requests against the actual external LLM infrastructure and local vector stores, proving the end-to-end integration works precisely as designed under real-world network conditions. This definitively proves the architecture's capability to orchestrate real LLM calls, handle API rate limits, and perform actual, mathematically sound semantic chunking.



## 4. Tutorial Plan

To ensure maximum simplicity and absolute ease of verification, the entire user journey and all critical test scenarios will be consolidated into a single, highly interactive, executable file.

*   **File Name:** You must execute the tutorial via the file explicitly named `tutorials/UAT_AND_TUTORIAL.py`.
*   **Technology:** This file is explicitly built as a `marimo` notebook. Marimo provides a reactive, reproducible, pure-Python environment that is vastly superior to standard Jupyter notebooks for this specific UAT purpose, as it guarantees a linear execution flow without hidden state bugs.
*   **Content Flow:** The single file will guide the user sequentially through the following explicit phases:
    1.  **Initialization:** Setting up the Pydantic system configuration, initializing the DI container, and explicitly displaying the current execution mode (Mock vs. Real) to the user.
    2.  **Ingestion Simulation:** Executing the file upload logic against the dummy `testfiles/test_text.txt` file to trigger the ingestion pipeline.
    3.  **Processing Visualization:** Executing the semantic chunking and RAPTOR tree generation LangGraph logic, printing the resulting heavily-nested Pydantic `GraphState` directly into the notebook for visual inspection.
    4.  **Interactive SQ3R:** Simulating a user answering an AI-generated question (with both correct and intentionally incorrect answers) to unlock a node and demonstrating the resulting Sandwich Feedback mechanism.
    5.  **Pivot Analysis:** Executing the MD-SKJ analysis, retrieving a subset of chunks based on a custom, predefined axis, and simulating the spatial re-arrangement.
    6.  **Export Demonstration:** Displaying the final generated Markdown text and rendering the resulting Mermaid.js diagram directly within the notebook's output cells, proving the To-Be system generation capability.



## 5. Tutorial Validation

Validation of the system's success is tied directly and exclusively to the flawless execution of this tutorial notebook. The matome platform is considered architecturally sound, functionally complete, and ready for production deployment when the following absolute validation criteria are met:

1.  **Execution:** The user (or an automated CI agent) can run `uv run marimo edit tutorials/UAT_AND_TUTORIAL.py` (or execute it headlessly via `uv run python tutorials/UAT_AND_TUTORIAL.py`) and the entire script runs linearly from top to bottom without raising a single Python exception, network timeout, or Pydantic validation error.
2.  **State Verification:** The deterministic mock responses (or real OpenRouter responses) successfully trigger the expected, predictable state changes in the strict domain models (e.g., transitioning a `RaptorNode` from `is_unlocked=False` to `is_unlocked=True` based on the simulated user answer).
3.  **Visual Proof:** The final output cells of the notebook clearly and undeniably demonstrate the mathematical transformation of the unstructured raw text into a highly structured, multi-dimensional format, culminating in the successful rendering of a syntactically valid Mermaid.js diagram.
