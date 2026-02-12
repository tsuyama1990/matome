# Cycle 05 User Acceptance Testing (UAT)

## 1. Test Scenarios

Cycle 05 is the final UAT, confirming that the entire Semantic Zooming and Interactive Refinement vision is realized.

### Scenario CYCLE05-01: Semantic Zooming (Drill Down)
**Priority:** Critical
**Description:** Verify the user can navigate from Wisdom down to Data.
**Steps:**
1.  **Preparation:** Launch the app with a loaded database.
2.  **Action:** Click on a Wisdom (L1) node. Then click "Zoom In" (or double-click).
3.  **Verification:** The list view should change to show only the Knowledge (L2) nodes that are children of the selected Wisdom.
4.  **Result Check:** The Breadcrumb bar should show "Home > Wisdom: [Summary...]".

### Scenario CYCLE05-02: Source Traceability (Evidence Check)
**Priority:** Critical
**Description:** Verify that any claim can be traced to original text.
**Steps:**
1.  **Preparation:** Select any node (L1, L2, or L3).
2.  **Action:** Click the "View Source" button.
3.  **Verification:** A modal or panel opens.
4.  **Result Check:** It should display the raw text chunks (L4) that contributed to this node. The user should be able to verify the summary against the source.

### Scenario CYCLE05-03: Full End-to-End User Journey
**Priority:** High
**Description:** A complete walkthrough of the "Knowledge Installation" process.
**Steps:**
1.  **Load:** Open the app.
2.  **Discover:** Read a Wisdom node. "Ah, I get the main idea."
3.  **Explore:** Zoom into Knowledge. "How does this work?"
4.  **Action:** Zoom into Information. "What do I do?"
5.  **Verify:** Check the Source. "Is this true?"
6.  **Refine:** Rewrite a node. "Make it fit my context."
7.  **Result Check:** The user leaves with a verified, personalized mental model.

## 2. Behavior Definitions

### Feature: Navigation & Traceability

**Scenario:** Zoom In
    **Given** the user is viewing a Wisdom node about "Compound Interest"
    **When** they click "Zoom In"
    **Then** the view should display Knowledge nodes like "Rule of 72" and "Exponential Growth"
    **And** the breadcrumb should update to reflect the path

**Scenario:** View Source
    **Given** a Knowledge node claiming "The Rule of 72 estimates doubling time"
    **When** "View Source" is clicked
    **Then** the original text chunk containing "Divide 72 by the interest rate..." should be displayed
