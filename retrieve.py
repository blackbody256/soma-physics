import re
import sqlite3

import numpy as np
import ollama

from config import DB_PATH, EMBED_MODEL, MIN_SCORE, OLLAMA_URL, TOP_K, USE_KEYWORD

client = ollama.Client(host=OLLAMA_URL)

STOP = set(
    """the and for with that this what why how does into from are was were will can
    you your have has its which when where who about there they them""".split()
)


class Index:
    def __init__(self, path=DB_PATH):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        rows = self.conn.execute(
            "SELECT id, source, page, topic, subtopic, text, embedding FROM chunks"
        ).fetchall()
        if not rows:
            raise RuntimeError("No chunks found. Run ingest.py first.")
        self.ids = [r[0] for r in rows]
        self.meta = {
            r[0]: {
                "id": r[0],
                "source": r[1],
                "page": r[2],
                "topic": r[3],
                "subtopic": r[4],
                "text": r[5],
            }
            for r in rows
        }
        self.matrix = np.vstack([np.frombuffer(r[6], dtype=np.float32) for r in rows])

    def embed_query(self, query: str):
        vec = client.embed(
            model=EMBED_MODEL,
            input=f"task: search result | query: {query}",
        ).embeddings[0]
        vec = np.asarray(vec, dtype=np.float32)
        norm = np.linalg.norm(vec)
        if norm == 0:
            return vec
        return vec / norm

    def vector_search(self, query: str, n: int = 10):
        sims = self.matrix @ self.embed_query(query)
        order = np.argsort(-sims)[:n]
        return [(self.ids[i], float(sims[i])) for i in order]

    def keyword_search(self, query: str, n: int = 10):
        if not USE_KEYWORD:
            return []
        words = [w for w in re.findall(r"[a-z]{3,}", query.lower()) if w not in STOP]
        if not words:
            return []
        match = " OR ".join(f'"{w}"' for w in words)
        rows = self.conn.execute(
            "SELECT rowid FROM chunks_fts WHERE chunks_fts MATCH ? ORDER BY bm25(chunks_fts) LIMIT ?",
            (match, n),
        ).fetchall()
        return [r[0] for r in rows]

    def search(self, query: str, k: int = TOP_K):
        vec = self.vector_search(query)
        kw = self.keyword_search(query)
        fused = {}
        for rank, (cid, _) in enumerate(vec):
            fused[cid] = fused.get(cid, 0.0) + 1.0 / (60 + rank)
        for rank, cid in enumerate(kw):
            fused[cid] = fused.get(cid, 0.0) + 1.0 / (60 + rank)
        best = vec[0][1] if vec else 0.0
        top = sorted(fused, key=fused.get, reverse=True)[:k]
        return [self.meta[c] for c in top], best, best >= MIN_SCORE
