# Voice-Type

Универсальный голосовой ввод текста — работает в любом приложении на iPhone и Mac.

Нажал кнопку → сказал → текст в буфере обмена → вставил куда нужно.

## Как работает

```
[iPhone / Mac] → аудио → [VPS API] → Deepgram Nova-2 → текст → clipboard
```

- **Сервер**: FastAPI на VPS, принимает аудио, отправляет в Deepgram, возвращает текст
- **Mac-клиент**: Python-скрипт с горячей клавишей (правый Command). Зажал → диктуешь → отпустил → текст в буфере
- **iPhone**: Apple Shortcuts — нажал → записал → текст скопирован

## Структура

```
server/          — API сервер (FastAPI + Deepgram Nova-2)
clients/mac/     — Mac-клиент (pynput + pyaudio)
clients/ios/     — Инструкция для Apple Shortcuts
SPEC.md          — Полная спецификация проекта
```

## Стек

- **API**: Python, FastAPI, uvicorn
- **Транскрибация**: Deepgram Nova-2 (русский, smart_format, пунктуация)
- **Mac**: pynput (горячая клавиша), pyaudio (запись), pyperclip (буфер), PyObjC (пилюля-индикатор)
- **iPhone**: Apple Shortcuts (Record Audio → POST → Copy)
- **VPS**: systemd + nginx reverse proxy
- **Безопасность**: Bearer-токен, лимит 25MB

## Деплой

Сервер работает на VPS (systemd service `voice-type.service`, порт 8100, nginx proxy на 80).

### Mac — установка и запуск

Один раз: положить токен в `clients/mac/.env` (`VOICETYPE_TOKEN=...`) и выполнить
`clients/mac/install.sh` — он ставит зависимости и включает автозапуск (launchd).

Дальше просто:
- Зажать правый Command → внизу экрана появляется пилюля с живой волной (как у Wispr Flow) — видно, что запись идёт
- Отпустить → пилюля показывает «обработку», затем «✓ Cmd+V» — текст в буфере
- Cmd+V для вставки

Проверить визуал без микрофона: `python3 voice_type.py --demo` (прокрутка всех состояний).
Лог агента: `/tmp/voicetype.log`.

### iPhone — настройка

Через приложение "Команды" (Shortcuts):
1. Record Audio
2. POST на API с Bearer-токеном
3. Получить значение "text" из ответа
4. Copy to Clipboard
