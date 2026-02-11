# Cycle 05: User Acceptance Testing (UAT)

## 1. Test Scenarios

### Scenario A: Verify Semantic Zooming
*   **ID**: S05-01
*   **Priority**: High
*   **Description**: Verify that the user can navigate from the Wisdom node down to specific Information nodes (L1 -> L2 -> L3) via the GUI.
*   **Preconditions**:
    *   `chunks.db` contains a hierarchy (Wisdom -> Knowledge -> Information).
    *   UI server is running.
*   **Steps**:
    1.  Launch the UI.
    2.  **View**: The Wisdom node (L1) is displayed.
    3.  **Check**: Are there child nodes listed (Knowledge layer)?
    4.  **Action**: Click on one of the child nodes.
    5.  **View**: The main view updates to show the selected Knowledge node (L2).
    6.  **Check**: Is the content more detailed (explaining "Why")?
    7.  **Check**: Are its children (Information layer) listed?
    8.  **Action**: Click a child again.
    9.  **View**: The main view updates to show the Information node (L3).
    10. **Check**: Does it contain actionable checklists?

### Scenario B: Verify Interactive Refinement
*   **ID**: S05-02
*   **Priority**: High
*   **Description**: Verify that the user can rewrite a node using natural language instructions.
*   **Preconditions**:
    *   UI server is running.
    *   Current view is on any node.
*   **Steps**:
    1.  Observe the current text of the node.
    2.  **Action**: Enter "Translate this to Japanese" (or "Make it simpler") in the refinement text box.
    3.  **Action**: Click "Refine".
    4.  **View**: Observe a loading indicator.
    5.  **View**: The node text updates to the new version.
    6.  **Check**: Is the text actually rewritten as requested?
    7.  **Check**: Is there an indication that this node was edited by the user?

## 2. Behavior Definitions (Gherkin)

### Feature: GUI Interaction

**Scenario: User zooms into a child node**
  **GIVEN** the user is viewing a Wisdom node
  **AND** the node has children (Knowledge nodes)
  **WHEN** the user clicks on a child card
  **THEN** the main view should replace the Wisdom node with the selected Knowledge node
  **AND** the breadcrumbs should update to show the path

**Scenario: User refines a node**
  **GIVEN** the user is viewing a node with text "Complex Theory"
  **WHEN** the user inputs "Explain like I'm 5" and clicks Refine
  **THEN** the system should call the refinement engine
  **AND** the view should update with the simplified text
