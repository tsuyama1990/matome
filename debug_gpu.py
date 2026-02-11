"""
Check GPU availability for SentenceTransformers.
"""

import torch
from sentence_transformers import SentenceTransformer

from domain_models.constants import (
    DEBUG_MSG_CUDA_AVAILABLE,
    DEBUG_MSG_CUDA_COUNT,
    DEBUG_MSG_CURRENT_DEVICE,
    DEBUG_MSG_DEVICE_NAME,
    DEBUG_MSG_INIT_MODEL,
    DEBUG_MSG_MODEL_DEVICE,
    DEFAULT_DEBUG_EMBEDDING_MODEL,
)


def check_gpu() -> None:
    """Print CUDA availability and device info."""
    # Using format strings as intended by the constants
    print(DEBUG_MSG_CUDA_AVAILABLE.format(torch.cuda.is_available()))  # noqa: T201
    if torch.cuda.is_available():
        print(DEBUG_MSG_CUDA_COUNT.format(torch.cuda.device_count()))  # noqa: T201
        print(DEBUG_MSG_CURRENT_DEVICE.format(torch.cuda.current_device()))  # noqa: T201
        print(DEBUG_MSG_DEVICE_NAME.format(torch.cuda.get_device_name(0)))  # noqa: T201

    print(DEBUG_MSG_INIT_MODEL)  # noqa: T201
    model = SentenceTransformer(DEFAULT_DEBUG_EMBEDDING_MODEL)
    print(DEBUG_MSG_MODEL_DEVICE.format(model.device))  # noqa: T201


if __name__ == "__main__":
    check_gpu()
