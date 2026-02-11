# Cycle 04 User Acceptance Testing (UAT)

## 1. Test Scenarios

### Scenario 04-A: Application Launch and Root Node Display
**Priority:** Critical
**Goal:** Verify that the Panel application can be launched, connect to the `DiskChunkStore`, and correctly display the Wisdom (Root) node using the MVVM architecture.

**Description:**
This is the first time the system has a visible interface. The user expects to run a command and see a web page with the core insight of their document. Failure here means the entire UI layer is non-functional.

**Execution Steps (Manual):**
1.  **Preparation:**
    *   Ensure `results/chunks.db` exists and contains a valid DIKW tree (from Cycle 02/03).
    *   Install `panel` and `watchfiles`.
2.  **Action:**
    *   Run `python -m matome.ui.app results/chunks.db --port 5006`. (Or equivalent command).
    *   Open `http://localhost:5006` in a web browser.
3.  **Verification:**
    *   **Page Load:** The page loads without 404 or 500 errors.
    *   **Content:** A card titled "Wisdom" (or similar) is visible.
    *   **Text:** The text inside the card matches the root summary of the document.
    *   **Style:** Ideally, the card has a visual distinction (e.g., gold border or specific icon) indicating it is the root.

**Success Criteria:**
*   The Panel server starts successfully.
*   The browser renders the initial view.
*   The correct data is fetched from the database and displayed via the ViewModel binding.

### Scenario 04-B: State Management (ViewModel)
**Priority:** High
**Goal:** Verify that the `InteractiveSession` correctly updates its internal state when the model changes, ensuring the foundation for future interactivity is solid.

**Description:**
Although the UI is simple, the backend state logic must be robust. We simulate UI interactions programmatically to ensure the ViewModel reacts correctly.

**Execution Steps (Python Script):**
1.  **Setup:**
    *   Initialize `InteractiveSession`.
    *   Mock the `InteractiveRaptorEngine` to return a dummy root node.
2.  **Action:**
    *   Call `session.load_tree("dummy.db")`.
    *   **Check:** `session.root_node` is not None.
    *   Call `session.select_node("node-123")`.
    *   **Check:** `session.selected_node_id` == "node-123".
3.  **Verification:**
    *   Use `param.watch` or a callback to verify that a change event was triggered when `root_node` was set.

**Success Criteria:**
*   The ViewModel's parameters reflect the loaded data.
*   State changes trigger the expected reactive events (essential for Panel updates).

## 2. Behavior Definitions (Gherkin)

### Feature: GUI Initialization

**Scenario: Launching Matome Canvas**
  Given a valid `chunks.db` containing a processed document tree
  When I launch the Matome UI application pointing to this database
  Then the application should start a web server
  And the initial view should display the Root Summary Node
  And the Root Node should be visually identified as "Wisdom"
