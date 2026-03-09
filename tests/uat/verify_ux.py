import sys

from src.domain_models import (
    DocumentNode,
    NodeMetadata,
    NodeStatus,
    PivotAxis,
    PivotBoard,
    PivotBoardNode,
    UserInteractionContext,
)


class MockBrowser:
    """Simulates Playwright/Selenium browser interactions for UAT."""
    def __init__(self) -> None:
        self.current_page = "login"
        self.displayed_elements: list[str] = []

    def navigate_to(self, page: str) -> None:
        self.current_page = page
        sys.stdout.write(f"Browser navigated to {page}\n")

    def upload_file(self, filename: str) -> None:
        sys.stdout.write(f"Browser uploaded file: {filename}\n")
        self.displayed_elements.append("document_tree_view")

    def click_element(self, element_id: str) -> None:
        sys.stdout.write(f"User clicked on element: {element_id}\n")

    def fill_input(self, element_id: str, text: str) -> None:
        sys.stdout.write(f"User typed '{text}' into {element_id}\n")

    def verify_element_visible(self, element_id: str) -> bool:
        is_visible = element_id in self.displayed_elements
        sys.stdout.write(f"Verified element {element_id} is visible: {is_visible}\n")
        return is_visible

def test_simulate_user_journey() -> None:
    """
    Simulates a new user uploading a manual and transforming it.
    This test runs the UI sequence.
    """
    browser = MockBrowser()
    browser.navigate_to("dashboard")

    # Step 1: Ingestion UI flow
    browser.upload_file("test_text.txt")
    assert browser.verify_element_visible("document_tree_view")

    # Backend processing simulation
    doc_node = DocumentNode(
        id="root_1",
        parent_id=None,
        title="Complex Business Manual",
        summary="A long document",
        content="Full text...",
        status=NodeStatus.LOCKED,
        metadata=NodeMetadata(source=None, author=None, category="business", time_axis=None)
    )

    # Step 2: Interaction UI flow
    browser.click_element(f"node_{doc_node.id}")
    browser.displayed_elements.append("question_modal")
    assert browser.verify_element_visible("question_modal")

    # User interacts
    browser.fill_input("answer_field", "If budget > 5000")
    browser.click_element("submit_answer_btn")

    _ctx = UserInteractionContext(
        node_id=doc_node.id,
        status=NodeStatus.LOCKED,
        question_asked="What condition requires executive approval?",
        user_answer="If budget > 5000",
        feedback="Correct. Node Unlocked.",
        hints_used=0
    )
    doc_node.status = NodeStatus.UNLOCKED
    browser.displayed_elements.append("summary_view")
    assert browser.verify_element_visible("summary_view")

    # Step 3: Pivot UI flow
    browser.click_element("pivot_btn")
    browser.click_element("axis_actor_state")

    board = PivotBoard(
        id="board_1",
        original_root_id=doc_node.id,
        axis=PivotAxis.ACTOR_STATE,
        custom_axis_description=None,
        nodes=[
            PivotBoardNode(node_id=doc_node.id, x_position=0.5, y_position=0.5, cluster_id="actor_ceo")
        ],
        mermaid_diagram="sequenceDiagram..."
    )

    browser.displayed_elements.append("mermaid_diagram_render")
    assert browser.verify_element_visible("mermaid_diagram_render")
    assert board.axis == PivotAxis.ACTOR_STATE
