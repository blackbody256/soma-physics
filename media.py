import os
import subprocess
import tempfile

import ollama

from config import CHAT_MODEL, KEEP_ALIVE, OLLAMA_URL, STRICT_OPTIONS
from model_router import LOCAL, chat as route_chat
from prompts import AUDIO_PROMPT, IMAGE_PROMPT

client = ollama.Client(host=OLLAMA_URL)
_whisper = None


def question_from_image(image_bytes: bytes, provider=LOCAL) -> str:
    resp = route_chat(
        provider=provider,
        model=CHAT_MODEL,
        keep_alive=KEEP_ALIVE,
        options=STRICT_OPTIONS,
        messages=[{"role": "user", "content": IMAGE_PROMPT, "images": [image_bytes]}],
    )
    return resp.message.content.strip()


def to_wav(audio_bytes: bytes) -> bytes:
    with tempfile.TemporaryDirectory() as tmp:
        src, dst = os.path.join(tmp, "input"), os.path.join(tmp, "output.wav")
        with open(src, "wb") as f:
            f.write(audio_bytes)
        subprocess.run(["ffmpeg", "-y", "-i", src, "-ac", "1", "-ar", "16000", dst], check=True, capture_output=True)
        with open(dst, "rb") as f:
            return f.read()


def transcribe_with_whisper(wav: bytes) -> str:
    global _whisper
    from faster_whisper import WhisperModel

    if _whisper is None:
        _whisper = WhisperModel("base", device="cpu", compute_type="int8")
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(wav)
        path = f.name
    try:
        segments, _ = _whisper.transcribe(path, language="en")
        return " ".join(s.text.strip() for s in segments)
    finally:
        os.remove(path)


def question_from_audio(audio_bytes: bytes) -> str:
    wav = to_wav(audio_bytes)
    try:
        resp = client.chat(
            model=CHAT_MODEL,
            keep_alive=KEEP_ALIVE,
            options={**STRICT_OPTIONS, "temperature": 0.0},
            messages=[{"role": "user", "content": AUDIO_PROMPT, "images": [wav]}],
        )
        text = resp.message.content.strip()
        if text:
            return text
    except ollama.ResponseError as err:
        print("Gemma audio failed, using faster-whisper:", err)
    return transcribe_with_whisper(wav)
