# Soma Physics

*Offline physics help for learners the new curriculum left behind.*

Uganda's competency-based curriculum asks learners to apply what they know. Many revision books and question banks were written for the previous curriculum, while rural learners often have less access to updated learning resources.

Soma Physics is an offline-first tutor built around Uganda's lower-secondary Physics syllabus. It runs a local Gemma model through Ollama on a laptop, and learners can connect from phones over a classroom hotspot. Once it is set up, local mode works without internet. An optional Gemini API mode is available for hosted-model prototyping.

## Why this exists

Many village schools have fewer learning resources than better-connected schools, and tools that depend on internet access may be unavailable where the gap is widest. Soma Physics puts a tutor on a laptop the school controls, so learning can continue without a reliable internet connection.

I studied Physics and saw how many learners struggle with it. That is why I started here.

## What it does

Learners can ask by text, photo, or voice. The tutor:

- Gives a hint first, then a full explanation
- Works through calculations step by step, with a safe calculator for arithmetic
- Retrieves supporting material from the NCDC syllabus using SQLite, embedding search, and keyword fallback
- Suggests practical activities of integration using locally available materials
- Runs in a lightweight mobile UI with no build step
- Offers optional QR codes so a class can join the hotspot quickly
- Supports local Gemma through Ollama, with an optional hosted Gemini API model

## How it works

```text
Learner's phone  ──(classroom hotspot)──>  Laptop running Soma Physics
                                              ├── FastAPI web app
                                              ├── Ollama (local Gemma + embeddings)
                                              └── SQLite (syllabus chunks)
```

In local mode, the phone is only a screen and all tutoring runs on the laptop. Hosted mode sends answer prompts and attached photos to Google's Gemini API; voice transcription and syllabus embeddings remain local.

## Quick start

1. Create a Python virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Start Ollama and pull the models:

```bash
ollama pull gemma4:e4b
ollama pull embeddinggemma
```

By default, Soma Physics answers with the local Gemma model. To enable the optional hosted Gemma 4 26B A4B model, set an API key before starting the app:

```bash
export GEMINI_API_KEY="your-api-key"
```

Hosted mode requires internet and sends the question and any attached photo to Google's API. Voice transcription and retrieval embeddings continue to run locally. Leave `GEMINI_API_KEY` unset to keep the app local-only. Never commit the API key.

3. Download the NCDC syllabus PDF yourself from [ncdc.go.ug](https://ncdc.go.ug/) and keep it under `data/`. The syllabus is copyrighted; do not commit its PDF or extracted text.

4. Ingest the PDF into the local SQLite database:

```bash
python ingest.py data/physics.pdf --pages 25-33 --reset
```

If text extraction is unreadable, try `--vision`. Vision ingestion needs the image-capable Gemma model.

5. Start the app:

```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

6. On the laptop, open `http://localhost:8000`. On a phone connected to the hotspot, open `http://<laptop-ip>:8000`.

Audio input needs `ffmpeg`. For the offline Whisper fallback, install `faster-whisper` and download its model before going offline.

## Status

Soma Physics is a work in progress. I want to shape it with Ugandan learners and teachers so it fits their classrooms. If you teach Physics or work with schools, feedback is welcome. Open an issue.

## Repository rules

- Do not commit PDFs or extracted syllabus text to this public repository.
- Keep downloaded materials in `data/` and ensure that directory stays untracked via `.gitignore`.
- Never commit API keys.

## License

MIT
