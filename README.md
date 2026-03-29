# Voice-Type

Голосовой ввод текста в любое приложение. Нажал → сказал → текст вставлен.

## Архитектура

```
[Клиент] → аудио → [API сервер] → Deepgram Nova-2 → текст → [Клиент] → вставка
```

## Компоненты

- `server/` — FastAPI backend (Deepgram transcription)
- `clients/mac/` — Desktop клиент (горячая клавиша)
- `clients/ios/` — Инструкция для Apple Shortcuts

## Быстрый старт

### Сервер
```bash
cd server
pip install -r requirements.txt
export DEEPGRAM_API_KEY="your-key"
export VOICETYPE_TOKEN="your-secret-token"
uvicorn main:app --host 0.0.0.0 --port 8100
```

### Mac клиент
```bash
cd clients/mac
pip install -r requirements.txt
export VOICETYPE_URL="https://your-vps:8100"
export VOICETYPE_TOKEN="your-secret-token"
python voice_type.py
```

## Безопасность
- API защищён токеном (VOICETYPE_TOKEN)
- HTTPS через nginx reverse proxy
- Лимит файла: 25MB
