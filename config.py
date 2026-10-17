import os
from pathlib import Path

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
CACHE_DIR = DATA_DIR / "cache"
DB_PATH = DATA_DIR / "tutor.db"
DATA_DIR.mkdir(exist_ok=True)
CACHE_DIR.mkdir(exist_ok=True)

CHAT_MODEL = os.environ.get("TUTOR_MODEL", "gemma4:e4b")
EMBED_MODEL = "embeddinggemma"
OLLAMA_URL = os.environ.get("TUTOR_OLLAMA_URL", "http://127.0.0.1:11434")

TOP_K = 4
MIN_SCORE = 0.35
CHUNK_CHARS = 1200
CHUNK_OVERLAP = 150
USE_KEYWORD = True

OPTIONS = {"temperature": 1.0, "top_p": 0.95, "top_k": 64, "num_ctx": 8192}
CALC_OPTIONS = {**OPTIONS, "temperature": 0.4}
STRICT_OPTIONS = {**OPTIONS, "temperature": 0.2}
KEEP_ALIVE = "30m"

USE_THINKING = True
SELF_CHECK = True
