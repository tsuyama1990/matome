# User Acceptance Test (UAT) Scenario & Tutorial Plan

## 1. Test Scenarios


### Scenario ID: UAT-01 - The "Aha!" Moment for a Product Manager (Quick Start)
**Priority:** High
**Description:** A Product Manager (PdM) wants to understand a dense legacy system manual and convert it into a modern workflow without falling into the "As-Is" trap.
**Detailed Steps & Expected Behaviors:**
1.  **Ingestion & Immediate Feedback (Survey):** The PdM begins by locating an incredibly dense, 200-page legacy business manual detailing outdated departmental approval workflows (e.g., `testfiles/legacy_approval_manual.txt`). They drag and drop this file into the matome web interface. The expected behavior is that the system instantly accepts the upload, returning a visual progress indicator. Within seconds, rather than presenting a wall of text, the system displays an elegant, high-level interactive tree structure (the RAPTOR graph) representing the core chapters and top-level concepts of the manual. The UI must remain completely responsive at 60fps during this rendering.
2.  **Cognitive Friction & Interaction (Question & Read):** The PdM notices a visually locked node titled "Special Executive Approval Processes". They attempt to click it to read the details. Instead of opening immediately, the Semantic Zoom UI halts and the AI tutor gently prompts them via a pop-up: "Based on your understanding of the surrounding chapters, what specific financial threshold do you think requires executive approval instead of just a line manager's?" This intentional friction forces the user to actively recall context. The user types, "Maybe if the budget is over £2000?" and hits enter.
3.  **Micro-Reward & Active Recall (Recite):** The system evaluates the answer. Because it's close, the node bursts open with a satisfying visual animation and a pleasant sound effect, revealing a highly dense, noise-free summary (generated via Chain of Density). After reading the summary, the user is prompted to recite. They activate their microphone and state, "Ah, executive approval is actually needed if the budget strictly exceeds £5000." The AI processes the audio and responds with positive Sandwich Feedback: "Great job! You correctly identified the £5000 threshold. Just remember it also applies to cross-departmental projects."
4.  **Radical Transformation (Pivot KJ):** Having understood the "As-Is" state, the PdM wants to design the "To-Be" system. They click the prominent "Pivot" button on the canvas and select the "Actor vs. State Transition" axis from the dropdown menu. The UI physics engine physically detaches the nodes from their original chapter-based hierarchy and dynamically re-arranges them into a new, multi-lane swimlane workflow layout, categorizing actions by 'Manager', 'Executive', and 'System'.
5.  **Final Export (Insight):** Satisfied with the new logical flow, the PdM clicks "Export PRD". The system instantly downloads a perfectly formatted Markdown document containing the new To-Be requirements and a syntactically valid Mermaid.js sequence diagram ready to be pasted into Jira or Confluence. The expected result is a profound "Aha!" moment where the user realizes they just converted a 200-page manual into a structured software design in minutes.

### Scenario ID: UAT-02 - Multi-Dimensional Analysis for a Consultant (Advanced)
**Priority:** Medium
**Description:** A business consultant needs to synthesise multiple disparate market reports to find a completely unique, cross-sectional angle for a high-stakes strategy pitch to corporate management.
**Detailed Steps & Expected Behaviors:**
1.  **Multi-Document Ingestion:** The consultant starts by uploading three entirely separate and massive documents simultaneously: a global market trend report, a highly technical competitor analysis specification, and a dense legal document regarding upcoming regulatory changes in Europe. The system processes these in parallel. The expected behavior is that the UI unifies these three distinct sources into a single, massive, interconnected knowledge tree without crashing or freezing, seamlessly linking related concepts across the different files.
2.  **Navigating the Semantic Forest:** The consultant faces a knowledge graph containing potentially thousands of nodes. They utilize the Semantic Zoom UI to dive deep into a cluster regarding "European Privacy Laws." Even while zoomed in at a high resolution to read specific legal clauses, the system constantly displays a minimap in the corner and an interactive breadcrumb trail at the top. The expected behavior is that the user never experiences the "lost in the middle" phenomenon; they can instantly snap back to the macro view by clicking the root breadcrumb.
3.  **Advanced Restructuring (Custom Pivot KJ):** The consultant realizes the original authors' structures are useless for their specific pitch. They trigger the Pivot KJ engine but choose to define a completely custom axis using natural language: "Plot these nodes on a matrix comparing 'Immediate Revenue Opportunities' against 'Long-term Regulatory Threats' specifically in the European Market." The LangGraph orchestration layer analyzes the vector embeddings across all three documents and physically reorganizes the nodes on the canvas into a custom four-quadrant matrix.
4.  **External Validation (Web-Grounding):** While reviewing a node placed in the "High Threat" quadrant regarding a specific AI regulation, the system actively intervenes. The AI highlights the node and presents a pop-up: "Web-Grounding Alert: Recent news articles from the past 48 hours indicate that the enforcement of this specific law has been officially delayed by two years. Would you like to automatically downgrade this threat and move the node to a lower-risk quadrant?" The consultant clicks "Accept."
5.  **Final Synthesis:** The consultant has successfully broken completely free of the original authors' narrative constraints. They have generated a completely novel, externally validated insight matrix that spans three different domains (market, technical, legal) without manually copy-pasting a single sentence. They export the visual matrix to a high-resolution image and the underlying data to a CSV for their presentation.

## 2. Behavior Definitions


### Feature: Secure Document Ingestion and Chunking
```gherkin
FEATURE: Highly Secure and Context-Aware Document Processing
  As an enterprise user processing sensitive corporate data
  I want to securely upload massive, complex documents
  So that the system can break them down into digestible semantic chunks without losing context or exposing my data to vulnerabilities.

  SCENARIO: Uploading a valid, complex text file successfully
    GIVEN the user has successfully authenticated and a valid API key is configured in their session
    AND the valid file "testfiles/legacy_approval_manual.txt" exists on their local machine
    WHEN the user initiates an asynchronous upload of the file via the main ingestion REST API
    THEN the system must immediately return a HTTP 202 Accepted status indicating background processing has started
    AND the background worker queue should successfully parse the text, normalize the noise, and generate a hierarchical RAPTOR tree
    AND the root node of this new knowledge tree must become accessible via the study session API within 5 seconds.

  SCENARIO: Defending against a malicious Path Traversal Attack
    GIVEN an attacker attempts to exploit the upload mechanism
    AND they craft a highly malicious payload attempting to force the system to read from "../../etc/passwd"
    WHEN the attacker submits this malicious path payload directly to the file upload endpoint bypassing the UI
    THEN the system's strict Pydantic input validation layer must immediately intercept the request
    AND the system must firmly reject the request with a HTTP 400 Bad Request status
    AND absolutely no file operations should be executed against the host operating system's root directory
    AND the security event must be logged internally for auditing purposes.

  SCENARIO: Handling massive files that exceed memory limits (Graceful Degradation)
    GIVEN the user attempts to upload an exceptionally large, 5-Gigabyte log file
    WHEN the ingestion pipeline begins processing the stream
    THEN the system must strictly process the data as iterators
    AND if the file violates the maximum configured chunk threshold, the system must gracefully halt processing for that specific file
    AND return a clear error to the user interface stating "File exceeds maximum processing limits" without crashing the entire backend worker pool.
```

### Feature: Frictionless Interactive Learning (SQ3R)
```gherkin
FEATURE: Enforced Frictionless Active Learning via Micro-Gamification
  As a dedicated learner trying to master complex technical concepts
  I want to be actively questioned before reading and forced to provide feedback after reading
  So that I can successfully bypass Ebbinghaus's forgetting curve and retain critical information in my long-term memory.

  SCENARIO: Successfully unlocking a node by demonstrating prior knowledge
    GIVEN a specific, high-value concept node within the RAPTOR tree is currently in a visually locked state
    WHEN the user explicitly requests to expand and read the detailed contents of the node
    THEN the system intervenes and presents a dynamically generated, context-aware question based on the node's hidden contents
    WHEN the user submits a text-based answer that semantically matches the core intent of the hidden node
    THEN the system immediately unlocks the node accompanied by positive visual feedback (micro-rewards)
    AND fully reveals the high-density Chain of Density (CoD) summary text to the user.

  SCENARIO: Reciting information verbally and receiving corrective Sandwich Feedback
    GIVEN the user has successfully unlocked, read, and comprehended a complex node
    WHEN the user utilizes the microphone to submit an audio transcript verbally summarising the core points of the node
    AND the AI transcribes the audio but detects that the user's summary contains a hallucinated fact absolutely not present in the original source chunk
    THEN the Context-Aware Hierarchical Merging (CAHM) logic engine explicitly flags the hallucination
    AND the system responds to the user with gentle "Sandwich Feedback" (Praise -> Correction -> Encouragement) to correct the error without destroying the user's learning motivation.

  SCENARIO: Failing the unlock question and utilizing the progressive hint system
    GIVEN the system has presented an adaptive question to unlock a node
    WHEN the user is completely stuck and explicitly clicks the "Show Hint" button instead of guessing
    THEN the system must not penalize the user
    AND it must progressively lower the cognitive difficulty by first revealing the first letter of the expected keyword
    AND if the user requests a second hint, the system transforms the open-ended question into a simpler multiple-choice format.
```

### Feature: Pivot KJ Multi-Dimensional Restructuring
```gherkin
FEATURE: Radical Multi-Dimensional Knowledge Restructuring
  As a system architect or business analyst
  I want to dynamically and physically rearrange the entire knowledge tree based on new analytical axes
  So that I can break free from the original document's structure and generate completely novel system requirements.

  SCENARIO: Pivoting a dense manual to a System Design Workflow Axis
    GIVEN a fully processed, massive document tree representing a highly unstructured legacy business manual
    WHEN the user explicitly triggers the Pivot KJ engine and selects the predefined "Actor vs. State Transition" multidimensional axis
    THEN the LangGraph orchestration layer maps the existing nodes and their metadata tags into a completely new spatial PivotBoard layout
    AND the newly formed visual clusters strictly represent distinct workflow stages (e.g., 'Pending', 'Approved') rather than the original chronological chapters
    AND the user interface physics engine elegantly animates the nodes moving to their new positions
    AND the system successfully generates a syntactically valid Mermaid.js sequence diagram code snippet directly derived from the dependencies mapped on the new board.

  SCENARIO: Rejecting a Web-Grounding AI suggestion during restructuring
    GIVEN the user has successfully pivoted the knowledge tree into a new workflow
    AND the Web-Grounding AI flags a node and suggests replacing a manual process with an automated AI check based on external internet best practices
    WHEN the user explicitly rejects the AI's suggestion because it violates strict internal company policy
    THEN the system must immediately dismiss the suggestion prompt
    AND the node must remain exactly in its current position without being modified
    AND the AI must not re-suggest the identical change during the current active session.
```

## 3. Tutorial Strategy


The tutorial strategy is meticulously designed to provide an absolutely frictionless, highly interactive "first-run" experience for both new developers evaluating the codebase and end-users experiencing the product. To ensure maximum accessibility and stability, we will strictly implement a dual-mode approach: "Mock Mode" and "Real Mode".

*   **Mock Mode (CI/CD and No-API-Key Execution):** This is the default, highly resilient state of the tutorial. When the tutorial script executes, it actively checks for the presence of the required OpenRouter API keys. If they are completely absent, the tutorial forcefully falls back to utilizing `unittest.mock` to mathematically simulate all external LLM responses, vector database embedding lookups, and web-grounding API calls. This guarantees that the tutorial can be run instantly, reliably, and completely free of charge in isolated CI/CD environments, or by curious users who simply want to experience the UI flow and application logic safely without managing external credentials.
*   **Real Mode (End-to-End Integration Verification):** If a valid `OPENROUTER_API_KEY` environment variable is explicitly detected by the system configuration, the tutorial seamlessly transitions into Real Mode. In this state, the tutorial hits the actual, live OpenRouter infrastructure and vector databases. This mode proves unequivocally that the complete end-to-end integration works exactly as architected, executing real semantic chunking, dynamic RAPTOR tree generation, and live Pivot KJ clustering against external APIs.

## 4. Tutorial Plan


To guarantee absolute simplicity, completely eliminate environment configuration headaches, and ensure effortless verification, we will consolidate the entire tutorial experience into a **SINGLE**, highly interactive Marimo notebook file.

*   **File Name:** `tutorials/UAT_AND_TUTORIAL.py`
*   **Content & Flow:** This solitary file will encapsulate the complete, definitive user journey. By utilizing Marimo's reactive notebook interface, it will guide the user sequentially through the following critical stages:
    1.  **Bootstrapping & Configuration:** Initializing the strict dependency injection container and explicitly displaying whether the system is currently running in Mock Mode or Real Mode.
    2.  **Simulated Ingestion:** Programmatically simulating the highly secure asynchronous upload of a sample legacy manual (e.g., `testfiles/test_text.txt`).
    3.  **Processing Execution:** Visually stepping through the execution of the semantic chunking algorithms and the subsequent LangGraph RAPTOR tree generation logic, printing the resulting tree hierarchy to the notebook interface.
    4.  **Interactive SQ3R Simulation:** Halting the notebook execution to simulate the "Question & Read" phase. The notebook will prompt the user to type an answer into a cell to unlock a specific semantic node, proving the cognitive friction mechanism works.
    5.  **Multi-Dimensional Pivot Execution:** Programmatically triggering the complex Pivot KJ analysis engine, forcing the nodes to reorganize along a new architectural axis.
    6.  **Final Export Verification:** Displaying the final, generated Markdown requirements document and directly rendering the resulting Mermaid.js diagram visually within the Marimo notebook interface to prove total success.

By strictly utilizing `marimo`, the user is empowered to execute cells sequentially, dynamically modify inputs (such as intentionally failing the AI's question to test the hint system), and immediately observe the reactive results. This completely satisfies all complex UAT requirements in a highly visual, totally reproducible, and easily debuggable manner.

## 5. Tutorial Validation


The formal validation process for this tutorial is strictly defined and easily executed by any developer. It involves running the command `uv run marimo edit tutorials/UAT_AND_TUTORIAL.py` (or alternatively executing it purely as a headless Python script) and formally confirming the following success criteria:

1.  **Execution Integrity:** The entire script must run synchronously from top to bottom without raising a single Python exception, proving the baseline architectural stability.
2.  **State Management Verification:** The simulated mock responses (or live real responses) must successfully and definitively trigger the expected state changes within the strict Pydantic domain models. For example, a correct answer must demonstrably transition a node's state from `locked=True` to `locked=False`.
3.  **Transformation Proof:** The final visual output rendered in the notebook must clearly and undeniably demonstrate the mathematical transformation of unstructured input text into a highly structured, multi-dimensional JSON or Markdown format, proving the core value proposition of the entire matome platform.
