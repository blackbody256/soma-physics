from contextlib import asynccontextmanager

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from config import BASE_DIR
from media import question_from_audio, question_from_image
from model_router import GEMMA_API, GEMMA_API_MODEL, LOCAL, gemma_api_available
from tutor import make_activity, tutor_answer, warm_up

MAX_UPLOAD = 10_000_000


@asynccontextmanager
async def lifespan(app):
    warm_up()
    yield


app = FastAPI(title="Soma Physics", lifespan=lifespan)


class AskRequest(BaseModel):
    question: str
    history: list[dict] = Field(default_factory=list)
    provider: str = LOCAL


class ActivityRequest(BaseModel):
    topic: str
    provider: str = LOCAL


def validate_provider(provider: str) -> str:
    if provider not in (LOCAL, GEMMA_API):
        raise HTTPException(400, "Choose local Gemma or Gemma 4 cloud.")
    if provider == GEMMA_API and not gemma_api_available():
        raise HTTPException(503, "Gemma 4 cloud is not configured. Set GEMINI_API_KEY on the app server.")
    return provider


def read_upload(file: UploadFile) -> bytes:
    data = file.file.read(MAX_UPLOAD + 1)
    if len(data) > MAX_UPLOAD:
        raise HTTPException(413, "File too large.")
    if not data:
        raise HTTPException(400, "Empty file.")
    return data


@app.get("/")
def home():
    return FileResponse(BASE_DIR / "static" / "index.html")


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/options")
def options():
    return {
        "providers": [
            {"id": LOCAL, "name": "Local Gemma", "available": True, "offline": True},
            {
                "id": GEMMA_API,
                "name": "Gemma 4 26B A4B · cloud",
                "available": gemma_api_available(),
                "offline": False,
                "model": GEMMA_API_MODEL,
            },
        ]
    }


@app.post("/api/ask")
def ask(req: AskRequest):
    provider = validate_provider(req.provider)
    question = req.question.strip()[:1000]
    if not question:
        raise HTTPException(400, "Please type a question.")
    return tutor_answer(question, req.history, provider)


@app.post("/api/ask-image")
def ask_image(file: UploadFile = File(...), provider: str = Form(LOCAL)):
    provider = validate_provider(provider)
    question = question_from_image(read_upload(file), provider)
    return {"question": question, **tutor_answer(question, provider=provider)}


@app.post("/api/ask-audio")
def ask_audio(file: UploadFile = File(...), provider: str = Form(LOCAL)):
    provider = validate_provider(provider)
    question = question_from_audio(read_upload(file))
    if not question:
        raise HTTPException(422, "I could not hear a question. Please try again.")
    return {"question": question, **tutor_answer(question, provider=provider)}


@app.post("/api/activity")
def activity(req: ActivityRequest):
    provider = validate_provider(req.provider)
    topic = req.topic.strip()[:200]
    if not topic:
        raise HTTPException(400, "Please name a topic.")
    return make_activity(topic, provider)
