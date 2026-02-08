# Cycle 05 Specification: KJ Method & Visualization

## 1. Summary

In this cycle, we focus on making the AI-generated structure accessible and editable by humans. We will implement an exporter for **Obsidian Canvas**, a JSON-based format used by the popular knowledge management tool Obsidian. This allows users to visualize the RAPTOR tree as a mind map, where summaries are "parent" nodes and chunks are "child" nodes. Users can then rearrange these nodes (KJ Method) to refine their understanding or correct the AI's logic.

## 2. System Architecture

New exporter module.

```
.
├── dev_documents/
├── src/
│   └── matome/
│       ├── ...
│       ├── exporters/
│       │   ├── __init__.py
│       │   ├── markdown.py
│       │   └── **obsidian.py** # Canvas JSON Generator
│       └── ...
├── tests/
│   └── **test_exporter.py**
└── pyproject.toml
```

## 3. Design Architecture

### 3.1. Obsidian Canvas JSON Schema (`src/matome/exporters/obsidian.py`)

The Canvas format is a JSON file containing:
*   `nodes`: List of objects (id, x, y, width, height, type="text", text).
*   `edges`: List of connections (id, fromNode, toNode).

### 3.2. Exporter Logic

*   **Class**: `ObsidianCanvasExporter`
*   **Method**: `export(tree: DocumentTree, output_path: Path)`
    *   **Node Generation**:
        *   Create a text node for the Root Summary at `(0, 0)`.
        *   Create nodes for Level 1 summaries below the Root.
        *   Create nodes for Level 2 chunks below Level 1 summaries.
    *   **Layout Algorithm**:
        *   Simple tree layout: Calculate `x` based on sibling index, `y` based on depth.
    *   **Edge Generation**:
        *   Connect Parent -> Child for all relationships in the `DocumentTree`.
    *   **File Writing**:
        *   Dump the dictionary to a `.canvas` JSON file.

## 4. Implementation Approach

1.  **Schema Definition**:
    *   Define Pydantic models for `CanvasNode` and `CanvasEdge` inside `obsidian.py` to ensure valid JSON structure.
2.  **Layout Logic**:
    *   Implement a recursive function to assign `(x, y)` coordinates.
    *   Start Root at (0, 0).
    *   Children go to `y + 400`.
    *   Spread children horizontally based on the total width of the subtree.
3.  **Integration**:
    *   Add a CLI command `matome export --format canvas` that calls this exporter.

## 5. Test Strategy

### 5.1. Unit Testing
*   **Target**: `src/matome/exporters/obsidian.py`
    *   **Test Case**: Create a dummy `DocumentTree` with 1 Root and 2 Children.
    *   **Test Case**: Verify the output JSON has 3 nodes and 2 edges.
    *   **Test Case**: Verify that `fromNode` and `toNode` IDs match existing nodes.

### 5.2. Integration Testing
*   **Scenario**:
    *   Run the full pipeline on `test_data/sample.txt`.
    *   Export to `sample.canvas`.
    *   Manually open in Obsidian (or verify file structure programmatically).
    *   Check if nodes overlap excessively (basic layout check).
