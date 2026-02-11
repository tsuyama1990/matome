# Cycle 04 User Acceptance Test (UAT): GUI Foundation

## 1. Test Scenarios

### Scenario ID: C04-01 (Initial Load & Rendering)
**Priority**: High
**Objective**: Verify that the application launches and renders the Root Node correctly.
**Description**:
As a user, when I run `matome canvas`, I expect to see the main window open and the "Wisdom" of the document displayed prominently.
**Steps**:
1.  **Preparation**: Ensure a valid `chunks.db` exists (from Cycle 02).
2.  **Execution**: Run `matome canvas path/to/chunks.db`.
3.  **Observation**:
    -   A browser window opens (or a URL is printed).
    -   The page has a title "Matome 2.0".
    -   There is a central card displaying the text of the Root Node.
    -   The metadata panel shows `dikw_level: wisdom`.

### Scenario ID: C04-02 (State Reactivity)
**Priority**: High
**Objective**: Verify that the MVVM binding works (changing state updates view).
**Description**:
As a developer, I need to ensure that the `InteractiveSession` correctly drives the UI.
**Steps**:
1.  **Execution**: Run the `tests/unit/test_viewmodel.py` suite.
2.  **Manual Check**:
    -   Add a temporary button in the UI code that calls `session.select_node(some_other_id)`.
    -   Click the button.
    -   Verify that the "Detail View" updates to show the new node's text.
    -   (Remove the button after test).

## 2. Behavior Definitions (Gherkin)

### Feature: Application Launch

**Scenario**: Opening the Canvas
  **GIVEN** a valid database file
  **WHEN** I run the `matome canvas` command
  **THEN** the Panel server should start
  **AND** the `InteractiveSession` should load the Root Node
  **AND** the UI should display the Root Node text

### Feature: Node Selection

**Scenario**: Viewing Node Details
  **GIVEN** the application is running
  **AND** the Root Node is currently selected
  **WHEN** the `session.selected_node` is updated to a child node (programmatically or via future UI)
  **THEN** the Detail View component should automatically re-render
  **AND** it should display the Child Node's text and metadata
