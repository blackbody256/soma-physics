import argparse
import re
import sqlite3
from pathlib import Path

import numpy as np
import ollama
import pymupdf as fitz

from config import (
    CACHE_DIR,
    CHAT_MODEL,
    CHUNK_CHARS,
    CHUNK_OVERLAP,
    DB_PATH,
    EMBED_MODEL,
    OLLAMA_URL,
    STRICT_OPTIONS,
    USE_KEYWORD,
)

client = ollama.Client(host=OLLAMA_URL)

TOPIC_RE = re.compile(r"^Topic\s+(\d+)\s*[:.]?\s*(.*)$", re.I)
SUBTOPIC_RE = re.compile(r"^Sub-?\s?topic\s+(\d+)\s*[:.]?\s*(.*)$", re.I)

VISION_PROMPT = """Transcribe this syllabus page into plain Markdown.
Rules:
- Keep headings such as Topic, Sub-topic, Competency, Learning Outcomes,
  Suggested Learning Activities and Sample Assessment Strategies.
- Write each heading on its own line, for example "Topic 5: Thermal Physics"
  and "Sub-topic 3: Transfer of Heat Energy".
- The page is a table with columns. Write each column as its own section, top to bottom.
- Put each learning outcome on its own line starting with its letter, for example "a. ...".
- Copy the words exactly. Do not add, explain or summarise anything."""


def looks_garbled(text: str) -> bool:
    chars = [c for c in text if not c.isspace()]
    if len(chars) < 50:
        return True
    readable = sum(c.isascii() and (c.isalnum() or c in ".,:;()-%/=+'\"") for c in chars)
    return readable / len(chars) < 0.7


def read_page(doc, stem: str, page_no: int, force_vision: bool) -> str:
    page = doc[page_no - 1]
    text = page.get_text()
    if not force_vision and not looks_garbled(text):
        print(f"  page {page_no}: text route")
        return text
    cache = CACHE_DIR / f"{stem}_p{page_no}.md"
    if cache.exists():
        print(f"  page {page_no}: vision route (cached)")
        return cache.read_text(encoding="utf-8")
    print(f"  page {page_no}: vision route, reading the page image ...")
    png = page.get_pixmap(dpi=150).tobytes("png")
    resp = client.chat(
        model=CHAT_MODEL,
        messages=[{"role": "user", "content": VISION_PROMPT, "images": [png]}],
        options=STRICT_OPTIONS,
    )
    text = resp.message.content
    cache.write_text(text, encoding="utf-8")
    return text


def clean_heading(text: str) -> str:
    return re.sub(r"\.{3,}.*$", "", text).strip(" .:-*#")


def split_sections(pages):
    topic, subtopic = "General", ""
    buf, start_page = [], None
    for page_no, text in pages:
        for raw in text.splitlines():
            line = raw.strip().lstrip("#* ").strip()
            t, s = TOPIC_RE.match(line), SUBTOPIC_RE.match(line)
            if t or s:
                if buf:
                    yield topic, subtopic, start_page, "\n".join(buf)
                    buf = []
                if t:
                    topic = f"Topic {t.group(1)}: {clean_heading(t.group(2))}"
                    subtopic = ""
                else:
                    subtopic = f"Sub-topic {s.group(1)}: {clean_heading(s.group(2))}"
                start_page = page_no
            if start_page is None:
                start_page = page_no
            if line:
                buf.append(line)
    if buf:
        yield topic, subtopic, start_page, "\n".join(buf)


def windows(text: str, size: int = CHUNK_CHARS, overlap: int = CHUNK_OVERLAP):
    out, start = [], 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            nl = text.rfind("\n", start + size // 2, end)
            if nl != -1:
                end = nl
        piece = text[start:end].strip()
        if len(piece) > 40:
            out.append(piece)
        if end >= len(text):
            break
        start = end - overlap
    return out


def embed_docs(chunks):
    inputs = [f"title: {c['subtopic'] or c['topic']} | text: {c['text']}" for c in chunks]
    vectors = []
    for i in range(0, len(inputs), 16):
        vectors.extend(client.embed(model=EMBED_MODEL, input=inputs[i : i + 16]).embeddings)
    arr = np.asarray(vectors, dtype=np.float32)
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return arr / norms


def init_db(conn, reset: bool):
    if reset:
        conn.executescript("DROP TABLE IF EXISTS chunks; DROP TABLE IF EXISTS chunks_fts;")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS chunks(
            id INTEGER PRIMARY KEY, source TEXT, page INTEGER,
            topic TEXT, subtopic TEXT, text TEXT, embedding BLOB)"""
    )
    if USE_KEYWORD:
        conn.execute("CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(text, topic, subtopic)")


def parse_pages(spec, total):
    if not spec:
        return list(range(1, total + 1))
    first, _, last = spec.partition("-")
    return list(range(int(first), int(last or first) + 1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--pages", help="1-based page range, e.g. 25-33")
    ap.add_argument("--vision", action="store_true", help="read every page as an image")
    ap.add_argument("--reset", action="store_true", help="delete existing chunks first")
    args = ap.parse_args()

    doc = fitz.open(args.pdf)
    stem = Path(args.pdf).stem[:40]
    pages = [(n, read_page(doc, stem, n, args.vision)) for n in parse_pages(args.pages, doc.page_count)]

    chunks = []
    for topic, subtopic, page_no, text in split_sections(pages):
        for piece in windows(text):
            chunks.append({
                "source": Path(args.pdf).name,
                "page": page_no,
                "topic": topic,
                "subtopic": subtopic,
                "text": piece,
            })
    if not chunks:
        raise SystemExit("No text found. Try --vision.")

    print(f"Embedding {len(chunks)} chunks ...")
    vectors = embed_docs(chunks)

    conn = sqlite3.connect(DB_PATH)
    init_db(conn, args.reset)
    for c, v in zip(chunks, vectors):
        cur = conn.execute(
            "INSERT INTO chunks(source, page, topic, subtopic, text, embedding) VALUES (?,?,?,?,?,?)",
            (c["source"], c["page"], c["topic"], c["subtopic"], c["text"], v.tobytes()),
        )
        if USE_KEYWORD:
            conn.execute(
                "INSERT INTO chunks_fts(rowid, text, topic, subtopic) VALUES (?,?,?,?)",
                (cur.lastrowid, c["text"], c["topic"], c["subtopic"]),
            )
    conn.commit()
    print(f"Stored {len(chunks)} chunks in {DB_PATH}")


if __name__ == "__main__":
    main()
