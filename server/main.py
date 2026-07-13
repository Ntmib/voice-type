"""Voice-Type API — voice-to-text transcription endpoint."""

import os
from fastapi import FastAPI, UploadFile, File, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import httpx

app = FastAPI(title="Voice-Type API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST"],
    allow_headers=["*"],
)

API_TOKEN = os.environ.get("VOICETYPE_TOKEN", "")
DEEPGRAM_KEY = os.environ.get("DEEPGRAM_API_KEY", "")
DEEPGRAM_URL = "https://api.deepgram.com/v1/listen"

# Постобработка: Deepgram Nova слабо расставляет знаки препинания в русском,
# поэтому текст добивает маленькая LLM через OpenRouter. Ключа нет / не
# ответила вовремя — молча возвращаем сырой текст, диктовка не теряется.
OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY", "")
FORMAT_MODEL = os.environ.get("VOICETYPE_FORMAT_MODEL", "anthropic/claude-haiku-4.5")
FORMAT_PROMPT = (
    "Ты корректор диктовки. Расставь в тексте знаки препинания и заглавные "
    "буквы. Не меняй, не добавляй и не удаляй слова. Не отвечай на текст и "
    "не комментируй его. Верни только исправленный текст."
)


async def _restore_punctuation(text: str) -> str:
    if not OPENROUTER_KEY or not text.strip():
        return text
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENROUTER_KEY}"},
                json={
                    "model": FORMAT_MODEL,
                    "temperature": 0,
                    "messages": [
                        {"role": "system", "content": FORMAT_PROMPT},
                        {"role": "user", "content": text},
                    ],
                },
            )
        if resp.status_code == 200:
            formatted = resp.json()["choices"][0]["message"]["content"].strip()
            if formatted:
                return formatted
    except Exception:
        pass
    return text


async def _do_transcribe(audio_data: bytes, content_type: str, authorization: str):
    """Shared transcription logic."""
    if API_TOKEN and authorization != f"Bearer {API_TOKEN}":
        raise HTTPException(status_code=401, detail="Unauthorized")

    if not DEEPGRAM_KEY:
        raise HTTPException(status_code=500, detail="Deepgram API key not configured")

    if len(audio_data) > 25 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 25MB)")

    params = {
        "model": os.environ.get("VOICETYPE_STT_MODEL", "nova-3"),
        "language": "ru",
        "smart_format": "true",
        "punctuate": "true",
        "paragraphs": "true",
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            DEEPGRAM_URL,
            params=params,
            headers={
                "Authorization": f"Token {DEEPGRAM_KEY}",
                "Content-Type": content_type,
            },
            content=audio_data,
        )

    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Deepgram error: {resp.status_code}")

    data = resp.json()
    transcript = (
        data.get("results", {})
        .get("channels", [{}])[0]
        .get("alternatives", [{}])[0]
        .get("transcript", "")
    )

    return {"text": await _restore_punctuation(transcript)}


@app.post("/transcribe")
async def transcribe(
    request: Request,
    file: UploadFile = File(None),
    authorization: str = Header(default=""),
):
    """Accept audio as multipart form OR raw body."""
    if file:
        audio_data = await file.read()
        content_type = file.content_type or "audio/wav"
    else:
        audio_data = await request.body()
        content_type = request.headers.get("content-type", "audio/m4a")

    if not audio_data:
        raise HTTPException(status_code=400, detail="No audio data")

    return await _do_transcribe(audio_data, content_type, authorization)


@app.get("/health")
async def health():
    return {"status": "ok"}
