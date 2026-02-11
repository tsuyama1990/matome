# Cycle 04: User Acceptance Testing (UAT)

## 1. Test Scenarios

### Scenario A: Verify GUI Launch
*   **ID**: S04-01
*   **Priority**: High
*   **Description**: Verify that the Matome UI application launches successfully and displays the initial wisdom node.
*   **Preconditions**:
    *   `chunks.db` exists with at least one wisdom node.
    *   System built with `panel` and `InteractiveSession`.
*   **Steps**:
    1.  Run `uv run matome ui chunks.db`.
    2.  Open `http://localhost:5006` in a web browser.
    3.  **Check**: Does the page load?
    4.  **Check**: Is the title "Matome 2.0"?
    5.  **Check**: Is the Wisdom node (L1) displayed prominently?

### Scenario B: Verify ViewModel State Management
*   **ID**: S04-02
*   **Priority**: Medium
*   **Description**: Verify that the ViewModel correctly loads data from the database.
*   **Preconditions**:
    *   `chunks.db` exists.
*   **Steps (Scripted)**:
    1.  Initialize `DiskChunkStore` and `InteractiveSession`.
    2.  Call `session.load_root()`.
    3.  **Check**: Is `session.current_node` set to a SummaryNode?
    4.  **Check**: Is `session.current_node.metadata.dikw_level` == "wisdom"?
    5.  **Check**: Is `session.status_message` empty (or "Ready")?

## 2. Behavior Definitions (Gherkin)

### Feature: Interactive Session (MVVM)

**Scenario: Loading initial wisdom**
  **GIVEN** an `InteractiveSession` initialized with a valid `DiskChunkStore`
  **WHEN** `load_root()` is called
  **THEN** the `current_node` parameter should be updated with the L1 Wisdom node
  **AND** any View bound to `current_node` should automatically re-render
