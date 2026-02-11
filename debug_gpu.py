import torch
from sentence_transformers import SentenceTransformer
import time

print(f"CUDA available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"CUDA device count: {torch.cuda.device_count()}")
    print(f"Current device: {torch.cuda.current_device()}")
    print(f"Device name: {torch.cuda.get_device_name(0)}")

print("\nInitializing SentenceTransformer (auto-detect)...")
start = time.time()
try:
    model = SentenceTransformer("intfloat/multilingual-e5-large")
    print(f"Model loaded in {time.time() - start:.2f}s")
    print(f"Model device: {model.device}")
except Exception as e:
    print(f"Failed to load model: {e}")
