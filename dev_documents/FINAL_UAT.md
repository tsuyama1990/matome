# Final User Acceptance Test (UAT) & Tutorial Plan

## 1. Tutorial Strategy

The goal of the tutorial strategy is to guide users from a state of "Information Overload" to "Knowledge Mastery" using Matome 2.0. We will structure the tutorials to deliver an immediate "Aha! Moment" followed by a deeper exploration of the system's capabilities.

### "Mock Mode" Strategy
To ensure that new users (and CI/CD pipelines) can experience the system without requiring an OpenAI API key or incurring costs, we will implement a "Mock Mode".
*   **Mechanism**: The `SummarizationAgent` and `VerifierAgent` will check for a specific environment variable (e.g., `MATOME_MOCK_MODE=true` or `OPENROUTER_API_KEY=mock`).
*   **Behavior**: When in mock mode, instead of calling the LLM, the agents will return pre-generated, high-quality responses stored in `tests/data/mock_responses/`. This ensures a deterministic and fast tutorial experience.
*   **Coverage**: The mock data will cover the "Quickstart" scenario completely.

### The "Aha! Moment" (Scenario A)
The first interaction must be magical. We will use the sample file `test_data/エミン流「会社四季報」最強の読み方.txt`.
1.  **Input**: A dense, 2000-character text about financial analysis.
2.  **Output**: A single, profound "Wisdom" node (e.g., "四季報は読むな、変化を感じろ。") displayed instantly.
3.  **Action**: The user clicks this node, and it expands into 3 distinct "Knowledge" branches (Mental Models) and further into "Action" items (Checklists).
4.  **Result**: The user realizes they have "downloaded" the author's brain into their own in seconds.

### The "Zoom-In" Thrill (Scenario B)
Once hooked, the user is invited to *disagree* with the AI.
1.  **Action**: The user selects an "Action" node (e.g., "Check PSR < 1").
2.  **Refinement**: They type, "Make this explanation simpler for a 10-year-old."
3.  **Result**: The node text transforms before their eyes into a relatable analogy (e.g., "PSR is like a popularity contest..."). This demonstrates the *Interactive* power of the system.

## 2. Notebook Plan

We will provide a set of Jupyter Notebooks in the `tutorials/` directory to facilitate this learning journey.

### `tutorials/01_quickstart.ipynb`: The "Knowledge Installation" Experience
*   **Objective**: Demonstrate the end-to-end flow from raw text to a navigable DIKW tree.
*   **Key Features**:
    *   Setup (Installation check).
    *   Loading the sample text.
    *   Running the `RaptorEngine` in `DIKW` mode (Mock supported).
    *   Visualizing the result using a simple static tree print (or embedded Panel view if possible).
*   **Target Audience**: First-time users.
*   **Execution Time**: < 2 minutes (Mock Mode), ~5 minutes (Real Mode).

### `tutorials/02_interactive_refinement.ipynb`: The "Thinking Partner" Workflow
*   **Objective**: Teach users how to refine and mold the knowledge graph.
*   **Key Features**:
    *   Loading a pre-generated tree (from `chunks.db`).
    *   Initializing the `InteractiveRaptorEngine`.
    *   Selecting a specific node by ID.
    *   Applying a `RefinementStrategy` (e.g., "Rewrite as a Socratic dialogue").
    *   Verifying the update in the database.
*   **Target Audience**: Power users, Analysts.

### `tutorials/03_advanced_configuration.ipynb`: Customizing the Brain
*   **Objective**: Show how to tweak the system for different domains (e.g., Medical, Legal).
*   **Key Features**:
    *   Defining a custom `PromptStrategy` (e.g., `LegalPrecedentStrategy`).
    *   Injecting this strategy into the `SummarizationAgent`.
    *   Adjusting clustering parameters (GMM thresholds) for finer/coarser granularity.
*   **Target Audience**: Developers, Domain Experts.

## 3. Validation Steps

The QA Agent (or human reviewer) should perform the following checks when running these notebooks.

### General Checks
*   [ ] **No API Key Crash**: `01_quickstart.ipynb` must run to completion without a real API key if `OPENROUTER_API_KEY` is unset or set to "mock".
*   [ ] **Environment**: All imports (`matome`, `panel`, `pandas`) must work without `ModuleNotFoundError` after `uv sync`.

### Notebook-Specific Checks

#### `01_quickstart.ipynb`
*   [ ] **Output Structure**: The final output must clearly show a hierarchy. The root node text should be short and abstract ("Wisdom"), while leaf nodes should be detailed ("Data/Information").
*   [ ] **Visualization**: If an ASCII tree is printed, indentation must correctly represent the depth (L1, L2, L3).

#### `02_interactive_refinement.ipynb`
*   [ ] **Refinement Success**: The notebook must show the "Before" and "After" text of a node. The "After" text must reflect the specific instruction given (e.g., if asked for "Japanese", the output is Japanese).
*   [ ] **DB Consistency**: A cell querying the SQLite DB (`SELECT text FROM summary_nodes WHERE id='...'`) must return the *updated* text, proving persistence.

#### `03_advanced_configuration.ipynb`
*   [ ] **Custom Strategy**: The notebook should successfully generate a summary using a user-defined class, proving the system's extensibility.
