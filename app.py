from contextlib import asynccontextmanager

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from config import BASE_DIR
from media import question_from_audio, question_from_image
from tutor import make_activity, tutor_answer, warm_up

MAX_UPLOAD = 10_000_000


@asynccontextmanager
async def lifespan(app):
    warm_up()
    yield


app = FastAPI(title="Offline Physics Tutor", lifespan=lifespan)


class AskRequest(BaseModel):
    question: str
    history: list[dict] = Field(default_factory=list)


class ActivityRequest(BaseModel):
    topic: str


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


@app.post("/api/ask")
def ask(req: AskRequest):
    question = req.question.strip()[:1000]
    if not question:
        raise HTTPException(400, "Please type a question.")
    return tutor_answer(question, req.history)


@app.post("/api/ask-image")
def ask_image(file: UploadFile = File(...)):
    question = question_from_image(read_upload(file))
    return {"question": question, **tutor_answer(question)}


@app.post("/api/ask-audio")
def ask_audio(file: UploadFile = File(...)):
    question = question_from_audio(read_upload(file))
    if not question:
        raise HTTPException(422, "I could not hear a question. Please try again.")
    return {"question": question, **tutor_answer(question)}


@app.post("/api/activity")
def activity(req: ActivityRequest):
    topic = req.topic.strip()[:200]
    if not topic:
        raise HTTPException(400, "Please name a topic.")
    return make_activity(topic)
