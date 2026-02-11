"""
Check GPU availability for SentenceTransformers.
"""

import torch
from sentence_transformers import SentenceTransformer


def check_gpu() -> None:
    """Print CUDA availability and device info."""
    print(f"CUDA available: {torch.cuda.is_available()}")  # noqa: T201
    if torch.cuda.is_available():
        print(f"CUDA device count: {torch.cuda.device_count()}")  # noqa: T201
        print(f"Current device: {torch.cuda.current_device()}")  # noqa: T201
        print(f"Device name: {torch.cuda.get_device_name(0)}")  # noqa: T201

    print("\nInitializing SentenceTransformer (auto-detect)...")  # noqa: T201
    model = SentenceTransformer("all-MiniLM-L6-v2")
    print(f"Model device: {model.device}")  # noqa: T201


if __name__ == "__main__":
    check_gpu()
