import subprocess


def test_main_execution() -> None:
    import sys

    # Run the main.py file and capture output
    result = subprocess.run([sys.executable, "main.py"], capture_output=True, text=True, check=True)  # noqa: S603

    # Check if legacy terminal output is retained
    assert "Hello from matome!" in result.stdout
