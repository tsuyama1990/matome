# Cycle 05 User Acceptance Testing (UAT)

## 1. Test Scenarios

### Scenario 05-A: Semantic Zooming (Drill-Down Navigation)
**Priority:** Critical
**Goal:** Verify that the "Matome Canvas" allows users to navigate the DIKW hierarchy visually, revealing lower levels of detail on demand (The "Zoom-In" Thrill).

**Description:**
The core value proposition of "Knowledge Installation" is the ability to start with the big picture (Wisdom) and explore the underlying structure (Knowledge) without being overwhelmed. This scenario tests the GUI's ability to handle this interaction.

**Execution Steps (Manual):**
1.  **Launch:** Start the app with a valid database.
2.  **Initial State:** Verify only the Root Node (Wisdom) is expanded/visible.
3.  **Action 1 (Zoom In):** Click on the Root Node card (or its "Expand" button).
4.  **Verification 1:**
    *   A new section/row appears below or beside the Root.
    *   This section contains the Level 2 (Knowledge) nodes.
    *   The text of these nodes aligns with the "Knowledge" definition (structural/explanatory).
5.  **Action 2 (Deep Dive):** Click on one of the Knowledge nodes.
6.  **Verification 2:**
    *   A third level appears (Information).
    *   It contains actionable checklists or bullet points.
7.  **Action 3 (Zoom Out):** Click the Root Node again (or "Collapse").
8.  **Verification 3:**
    *   The lower levels (Knowledge/Information) disappear or fold up.

**Success Criteria:**
*   Navigation is fluid (instant response since data is local).
*   The hierarchy is visually clear (indentation, connecting lines, or column layout).
*   No "ghost nodes" or rendering glitches.

### Scenario 05-B: Interactive Refinement via Chat
**Priority:** High
**Goal:** Verify that the user can modify the content of the tree using natural language instructions through the GUI, completing the feedback loop (The "Refinement" Action).

**Description:**
This tests the full stack: UI input -> ViewModel state -> Interactive Engine -> LLM -> Database -> UI update. A failure here breaks the "Interactive" promise.

**Execution Steps (Manual):**
1.  **Launch:** Start the app.
2.  **Select:** Click on a specific node (e.g., a "Knowledge" node about "Marketing Strategy").
3.  **Action:**
    *   Locate the "Refine" or "Edit" button/input area.
    *   Type: "Rewrite this to be more concise and use a bulleted list."
    *   Click "Submit" (or Enter).
4.  **Verification (Process):**
    *   A loading indicator (spinner/progress bar) appears on the specific node card.
    *   The UI remains responsive (not frozen) during generation.
5.  **Verification (Result):**
    *   After a few seconds, the loading indicator disappears.
    *   The text in the card updates to the new version.
    *   The new text is indeed concise and bulleted (LLM compliance).
    *   (Optional) Reload the page to confirm persistence.

**Success Criteria:**
*   The refinement request is processed successfully.
*   Visual feedback is provided during the async operation.
*   The database is updated correctly.

## 2. Behavior Definitions (Gherkin)

### Feature: Semantic Navigation

**Scenario: Expanding Wisdom to Reveal Knowledge**
  Given the Matome Canvas is displaying the Root Wisdom Node
  When I click the "Expand" control on the Wisdom Node
  Then the interface should display the child Knowledge Nodes associated with that Wisdom
  And the layout should visually indicate the parent-child relationship

### Feature: GUI-Based Refinement

**Scenario: Refining a Node via Text Input**
  Given I have selected a node in the Matome Canvas
  When I enter the instruction "Make it funnier" into the refinement input
  And I submit the request
  Then the application should indicate a "Processing" state for that node
  And the backend `InteractiveRaptorEngine` should be invoked with the instruction
  And upon completion, the node's text should update to a humorous version
  And the change should be persisted to the database
