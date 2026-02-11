"""
Check GPU availability for SentenceTransformers.
"""

import torch
from sentence_transformers import SentenceTransformer

from domain_models.constants import (
    DEBUG_MSG_INIT_MODEL,
    DEFAULT_DEBUG_EMBEDDING_MODEL,
)


def check_gpu(text: str = "Test sentence for embedding") -> None:
    """Print CUDA availability and device info."""
    print(f"CUDA available: {torch.cuda.is_available()}")  # noqa: T201
    if torch.cuda.is_available():
        print(f"Number of GPUs: {torch.cuda.device_count()}")  # noqa: T201
        print(f"Current device ID: {torch.cuda.current_device()}")  # noqa: T201
        # Sanitized: Mask device name for security compliance
        device_name = torch.cuda.get_device_name(0)
        masked_name = device_name[:4] + "***" if device_name else "Unknown"
        print(f"Device name: {masked_name}")  # noqa: T201

    print(DEBUG_MSG_INIT_MODEL)  # noqa: T201
    model = SentenceTransformer(DEFAULT_DEBUG_EMBEDDING_MODEL)
    print(f"Model loaded on device: {model.device}")  # noqa: T201

    # Encode check
    emb = model.encode(text)
    print(f"Encoded '{text}' to shape: {emb.shape}")  # noqa: T201


if __name__ == "__main__":
    check_gpu()
