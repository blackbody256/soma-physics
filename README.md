# Offline Physics Tutor

An offline AI physics tutor for Uganda's competence-based lower secondary curriculum. It blends local retrieval over the NCDC syllabus with a local Gemma 4 model served via Ollama, and it exposes a mobile-friendly web app over a classroom hotspot.

## Features

- Local tutoring via Gemma 4 and Ollama
- Retrieval from the NCDC syllabus using SQLite + embedding search + keyword fallback
- Socratic hints before final answers
- Calculator tool for safe physics calculations
- Activities of integration generated from the syllabus
- Photo and voice question input
- Lightweight mobile UI with no build step
- Optional QR codes for classroom hotspot access

## Quick start

1. Create a Python virtual environment.
2. Install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

3. Start Ollama and pull the model:

```bash
ollama pull gemma4:e4b
ollama pull embeddinggemma
```

4. Download the NCDC syllabus PDF yourself from [ncdc.go.ug](https://ncdc.go.ug) and keep it under `data/`. The syllabus is copyrighted; do not commit its PDF or extracted text.

5. Ingest the downloaded PDF into the local SQLite database:

```bash
python ingest.py data/physics.pdf --pages 25-33 --reset
```

If text extraction is unreadable, try `--vision`. Vision ingestion requires the image-capable Gemma model.

6. Start the app:

```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

7. Open the app on the same machine or on a phone connected to the hotspot at `http://<laptop-ip>:8000`.

Audio input also requires `ffmpeg`. For the offline Whisper fallback, install the optional `faster-whisper` package and download its model before using the app offline.

## Repo rules

- Do not commit PDFs or extracted syllabus text to the public repo.
- Keep all downloaded materials in `data/` and ensure that directory stays untracked via `.gitignore`.
- Use the local model and local syllabus only.

## License

MIT
