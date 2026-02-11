# Cycle 03: User Acceptance Testing (UAT)

## 1. Test Scenarios

These scenarios verify the correctness of the **Interactive Engine Backend**.

### Scenario 1: Retrieve Node Structure
**Priority**: High
**Goal**: Verify that the engine can efficiently retrieve a node and its children for navigation.
- **Steps**:
  1. Initialize `InteractiveRaptorEngine` with a populated `DiskChunkStore`.
  2. Call `get_node(root_id)`.
  3. Verify the node object is returned correctly.
  4. Call `get_children(root_id)`.
  5. Verify a list of child nodes is returned.

### Scenario 2: Single Node Refinement
**Priority**: Critical
**Goal**: Verify that a user can rewrite a specific node using natural language instructions.
- **Steps**:
  1. Select a target node (e.g., L3 Information).
  2. Note its original text and embedding.
  3. Call `engine.refine_node(node_id, instruction="Rewrite this for a 5-year-old")`.
  4. **Verification**:
     - The returned node has new text.
     - The text is simpler (subjective, but check length/complexity).
     - The node's embedding has been updated in the vector store.
     - `metadata.is_user_edited` is `True`.
     - `metadata.refinement_history` contains the instruction.

### Scenario 3: Concurrency Safety (Simulated)
**Priority**: Medium
**Goal**: Ensure that the database remains consistent even if the GUI tries to read while the engine is writing.
- **Steps**:
  1. Start a background thread that constantly reads random nodes from the store.
  2. In the main thread, perform a series of `refine_node` operations.
  3. Run for 5-10 seconds.
  4. **Verification**: No exceptions (e.g., `sqlite3.OperationalError: database is locked`) are raised. The final state of the DB is consistent.

## 2. Behavior Definitions (Gherkin)

### Feature: Interactive Refinement

**Scenario: User rewrites a node**
  GIVEN an existing summary node with ID `node_123`
  AND the user provides an instruction "Make it more concise"
  WHEN I call `refine_node('node_123', 'Make it more concise')`
  THEN the system should generate a new summary based on the node's original source chunks
  AND the new summary should replace the old text in the database
  AND the modification should be logged in `refinement_history`.

**Scenario: Reading children**
  GIVEN a parent node with ID `parent_1`
  AND multiple child nodes linked to `parent_1` in the database
  WHEN I call `get_children('parent_1')`
  THEN I should receive a list of `SummaryNode` objects corresponding to the children
  AND the list should be sorted by index or some logical order.
