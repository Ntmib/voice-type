# Voice-Type

Универсальный голосовой ввод текста в стиле Wispr Flow — работает в любом
приложении на Mac и iPhone.

Зажал клавишу → внизу экрана пилюля с живой волной → сказал → отпустил →
текст с расставленной пунктуацией в буфере обмена → Cmd+V.

## Как работает

```
[Mac / iPhone] → аудио → [твой VPS] → Deepgram Nova-3 → LLM-пунктуация → текст
```

- **Сервер** — FastAPI: принимает аудио, распознаёт через Deepgram,
  расставляет знаки препинания маленькой LLM через OpenRouter (опционально),
  возвращает текст
- **Mac-клиент** — Python: зажал правый Cmd → запись с плавающей пилюлей-индикатором
  (живая волна, состояния «обработка» / «готово» / «ошибка»), отпустил → текст в буфере
- **iPhone** — Apple Shortcuts: нажал → записал → текст скопирован

## Структура

```
server/          — API сервер (FastAPI + Deepgram + OpenRouter)
clients/mac/     — Mac-клиент (pynput + pyaudio + PyObjC-оверлей)
clients/ios/     — Инструкция для Apple Shortcuts
SPEC.md          — Спецификация проекта
```

## Развернуть свой сервер

Нужны: VPS с Python 3.10+, ключ [Deepgram](https://console.deepgram.com)
(есть бесплатный кредит), опционально ключ [OpenRouter](https://openrouter.ai)
для пунктуации.

```bash
cd server
python3 -m venv venv && venv/bin/pip install -r requirements.txt
cp .env.example .env   # заполни ключи
venv/bin/python3 -m uvicorn main:app --host 127.0.0.1 --port 8100
```

Для продакшена — systemd-сервис + nginx reverse proxy на 80/443.
Авторизация — Bearer-токен (`VOICETYPE_TOKEN`), лимит аудио 25MB.

## Установить Mac-клиент

```bash
cd clients/mac
cp .env.example .env   # адрес сервера + токен
./install.sh
```

Скрипт ставит зависимости, собирает мини-приложение VoiceType.app и включает
автозапуск (launchd). При первом запуске macOS попросит два разрешения для
VoiceType: «Универсальный доступ» и «Мониторинг ввода», плюс микрофон при
первой записи.

Дальше:
- **Зажать правый Command** → пилюля с волной = запись идёт
- **Отпустить** → «обработка» → «✓ Cmd+V» = текст в буфере
- **Cmd+V** — вставить

Проверка визуала без микрофона: `python3 voice_type.py --demo`.
Лог: `/tmp/voicetype.log`.

## Настроить iPhone

См. [clients/ios/README.md](clients/ios/README.md) — команда в Apple
Shortcuts из 5 действий, вешается на двойной тап по задней крышке.

## Лицензия

MIT
