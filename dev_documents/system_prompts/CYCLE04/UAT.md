# Cycle 04 User Acceptance Testing (UAT)

## 1. Test Scenarios

Cycle 04 focuses on verifying the foundational UI logic and state synchronization.

### Scenario CYCLE04-01: UI Launch
**Priority:** High
**Description:** Verify that the application launches without crashing.
**Steps:**
1.  **Preparation:** Have a valid `chunks.db`.
2.  **Execution:** Run `uv run matome serve`.
3.  **Verification:** A browser window (or localhost URL) should open.
4.  **Result Check:** The default dashboard should be visible, showing at least the Wisdom (L1) nodes.

### Scenario CYCLE04-02: Node Selection & Detail View
**Priority:** High
**Description:** Verify that clicking a node updates the detail panel.
**Steps:**
1.  **Preparation:** Launch the app.
2.  **Action:** Click on a node in the navigation pane.
3.  **Verification:** Observe the detail pane.
4.  **Result Check:** The detail pane should display the text of the selected node. The "Refine" button should become active.

### Scenario CYCLE04-03: Refinement Workflow (Mock)
**Priority:** Medium
**Description:** Verify the state changes during refinement (UI feedback).
**Steps:**
1.  **Preparation:** Select a node.
2.  **Action:** Enter "Rewrite this" in the refinement box and click "Submit".
3.  **Verification:** Observe the UI state.
4.  **Result Check:** The UI should show a "Processing..." indicator or disable the input. Once complete (even if mocked), the new text should appear in the detail pane.

## 2. Behavior Definitions

### Feature: GUI State Management

**Scenario:** Initial Load
    **Given** a database with nodes
    **When** the `InteractiveSession` is initialized
    **Then** `current_level` should be `WISDOM` (default)
    **And** `selected_node` should be `None`

**Scenario:** Refinement Submission
    **Given** a session with a `selected_node`
    **And** a user instruction "Make it shorter"
    **When** `submit_refinement()` is called
    **Then** `is_refining` should become `True`
    **And** the engine's `refine_node` method should be invoked
    **And** after completion, `is_refining` should become `False`
    **And** `selected_node` should reflect the updated content
