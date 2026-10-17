 # Soma Physics

*Offline physics help for learners the new curriculum left behind.*

Uganda's competency-based curriculum asks learners to apply what they know. Most revision books and question banks were written for the old one, and rural learners have the least access to new material.

Soma Physics is an offline-first tutor built on Uganda's lower-secondary Physics syllabus. It runs a local Gemma model through Ollama on one laptop, and learners connect from their phones over a classroom hotspot. Once it's set up, no internet is needed.

## Why this exists

Many village schools have far fewer learning resources than better-connected schools, and tools that depend on internet access tend to fail exactly where the gap is widest. Soma Physics takes a different route: put the tutor on a laptop the school controls, so learning doesn't depend on a connection that may not be there.

I studied Physics and saw how many learners struggle with it. That is why I started here.

## What it does

Learners can ask by text, photo, or voice. The tutor:

- Gives a hint first, then a full explanation (Socratic, not just answers)
- Works through calculations step by step, with a safe calculator for the arithmetic
- Points to the NCDC syllabus topic behind the answer, using retrieval over the syllabus (SQLite, embedding search, keyword fallback)
- Suggests practical activities of integration using materials found locally
- Runs in a lightweight mobile UI with no build step
- Offers optional QR codes so a class can join the hotspot quickly

## How it works

```
Learner's phone  ──(classroom hotspot)──>  Laptop running Soma Physics
                                              ├── FastAPI web app
                                              ├── Ollama (Gemma 4 + embeddings)
                                              └── SQLite (syllabus chunks)
```

The phone is only a screen. All the thinking happens on the laptop.

## Quick start

1. Create a Python virtual environment and install dependencies:

```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Start Ollama and pull the models:

```
ollama pull gemma4:e4b
ollama pull embeddinggemma
```

3. Download the NCDC syllabus PDF yourself from [ncdc.go.ug](https://ncdc.go.ug/) and keep it under `data/`. The syllabus is copyrighted, so do not commit the PDF or its extracted text.

4. Ingest the PDF into the local SQLite database:

```
python ingest.py data/physics.pdf --pages 25-33 --reset
```

If text extraction is unreadable, try `--vision`. Vision ingestion needs the image-capable Gemma model.

5. Start the app:

```
uvicorn app:app --host 0.0.0.0 --port 8000
```

6. On the laptop, open `http://localhost:8000`. On a phone connected to the hotspot, open `http://<laptop-ip>:8000`.

## Optional extras

- Audio input needs `ffmpeg`.
- For the offline Whisper fallback, install `faster-whisper` and download its model before going offline.

## Status

Soma Physics is a work in progress. I want to shape it with Ugandan learners and teachers so it fits their classrooms. If you teach Physics or work with schools, feedback is very welcome. Open an issue.

## Repo rules

- Do not commit PDFs or extracted syllabus text to this public repo.
- Keep all downloaded materials in `data/` and make sure that folder stays untracked via `.gitignore`.
- Use the local model and local syllabus only.
