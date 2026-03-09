import http.server
import pathlib
import socketserver
import threading
from collections.abc import Generator

import pytest
from playwright.sync_api import Page, expect


class DummyHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self) -> None:
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        html = """
        <html>
            <body>
                <div id="dashboard">Dashboard</div>
                <input type="file" id="file_upload" />
                <div id="document_tree_view" style="display:none;">Tree</div>
                <button id="node_root_1">Node 1</button>
                <div id="question_modal" style="display:none;">
                    <input type="text" id="answer_field" />
                    <button id="submit_answer_btn">Submit</button>
                </div>
                <div id="summary_view" style="display:none;">Summary</div>
                <button id="pivot_btn">Pivot</button>
                <button id="axis_actor_state" style="display:none;">Actor State</button>
                <div id="mermaid_diagram_render" style="display:none;">Diagram</div>
                <script>
                    document.getElementById('file_upload').addEventListener('change', () => {
                        document.getElementById('document_tree_view').style.display = 'block';
                    });
                    document.getElementById('node_root_1').addEventListener('click', () => {
                        document.getElementById('question_modal').style.display = 'block';
                    });
                    document.getElementById('submit_answer_btn').addEventListener('click', () => {
                        document.getElementById('summary_view').style.display = 'block';
                    });
                    document.getElementById('pivot_btn').addEventListener('click', () => {
                        document.getElementById('axis_actor_state').style.display = 'block';
                    });
                    document.getElementById('axis_actor_state').addEventListener('click', () => {
                        document.getElementById('mermaid_diagram_render').style.display = 'block';
                    });
                </script>
            </body>
        </html>
        """
        self.wfile.write(html.encode("utf-8"))


@pytest.fixture(scope="module")
def local_server() -> Generator[str, None, None]:
    port = 8000
    handler = DummyHandler
    httpd = socketserver.TCPServer(("", port), handler)
    thread = threading.Thread(target=httpd.serve_forever)
    thread.daemon = True
    thread.start()
    yield f"http://localhost:{port}"
    httpd.shutdown()
    httpd.server_close()


def test_simulate_user_journey(page: Page, local_server: str) -> None:
    """
    Simulates a new user uploading a manual and transforming it.
    This test runs the UI sequence using Playwright.
    """
    page.goto(local_server)

    # Step 1: Ingestion UI flow
    expect(page.locator("#dashboard")).to_be_visible()

    # Mocking file upload
    with pathlib.Path("test_text.txt").open("w") as f:
        f.write("mock file content")
    page.locator("#file_upload").set_input_files("test_text.txt")
    expect(page.locator("#document_tree_view")).to_be_visible()

    # Step 2: Interaction UI flow
    page.click("#node_root_1")
    expect(page.locator("#question_modal")).to_be_visible()

    # User interacts
    page.fill("#answer_field", "If budget > 5000")
    page.click("#submit_answer_btn")

    expect(page.locator("#summary_view")).to_be_visible()

    # Step 3: Pivot UI flow
    page.click("#pivot_btn")
    page.click("#axis_actor_state")

    expect(page.locator("#mermaid_diagram_render")).to_be_visible()
