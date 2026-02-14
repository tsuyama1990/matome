import logging
import time

import torch
from sentence_transformers import SentenceTransformer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info(f"CUDA available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    logger.info(f"CUDA device count: {torch.cuda.device_count()}")
    logger.info(f"Current device: {torch.cuda.current_device()}")
    logger.info(f"Device name: {torch.cuda.get_device_name(0)}")

logger.info("\nInitializing SentenceTransformer (auto-detect)...")
start = time.time()
try:
    model = SentenceTransformer("intfloat/multilingual-e5-large")
    logger.info(f"Model loaded in {time.time() - start:.2f}s")
    logger.info(f"Model device: {model.device}")
except Exception:
    logger.exception("Failed to load model")
