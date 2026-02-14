import socket
import subprocess
import time

import pytest
import requests

from domain_models.manifest import NodeMetadata, SummaryNode
from domain_models.types import DIKWLevel
from matome.utils.store import DiskChunkStore


def get_free_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('', 0))
    port = s.getsockname()[1]
    s.close()
    return port

@pytest.fixture
def test_db_path(tmp_path):
    db_path = tmp_path / "test_chunks.db"
    store = DiskChunkStore(db_path=db_path)

    # Create a minimal tree
    root = SummaryNode(
        id="root",
        text="Wisdom Node Text",
        level=3,
        children_indices=[],
        metadata=NodeMetadata(dikw_level=DIKWLevel.WISDOM)
    )
    store.add_summary(root)
    store.close()
    return db_path

def test_serve_command(test_db_path):
    """
    Test that 'matome serve' starts a server and serves content.
    """
    port = get_free_port()
    # Construct command: uv run matome serve <db_path> --port <port>
    # Note: 'matome serve' might not support --port directly if not implemented yet.
    # But panel serve does. If CLI wraps panel, we need to pass args.
    # Assuming 'matome serve' just starts on default port or we can control it.
    # Let's assume for now we use default or a specific flag if we implement it.
    # If not, we might conflict with other tests running in parallel?
    # For now, let's try to run it.

    # Check if 'matome serve' exists in CLI (it doesn't yet).
    # This test is expected to fail or hang if not implemented.

    # Command to run from repo root
    # Use python -m to ensure we run the code we just wrote
    cmd = ["uv", "run", "python", "-m", "matome.cli", "serve", str(test_db_path), "--port", str(port)]

    # Start process
    proc = subprocess.Popen(  # noqa: S603
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        # Poll for server availability
        timeout = 30
        start_time = time.time()
        url = f"http://localhost:{port}"

        while time.time() - start_time < timeout:
            try:
                response = requests.get(url, timeout=1)
                if response.status_code == 200:
                    assert "Wisdom Node Text" in response.text or "Matome" in response.text
                    break
            except requests.ConnectionError:
                time.sleep(0.5)
        else:
            # Check if process died
            if proc.poll() is not None:
                stdout, stderr = proc.communicate()
                pytest.fail(f"Server process died. Stdout: {stdout}\nStderr: {stderr}")

                # Capture output before failing
                proc.terminate()
                try:
                    stdout, stderr = proc.communicate(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    stdout, stderr = proc.communicate()
                pytest.fail(f"Server did not start in time. Stdout: {stdout}\nStderr: {stderr}")

    finally:
        proc.terminate()
        proc.wait()
