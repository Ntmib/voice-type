# Voice-Type iOS Shortcut

## Настройка (2 минуты)

1. Открой приложение **Shortcuts** (Команды) на iPhone
2. Создай новую команду:
   - **Record Audio** (Записать аудио) — качество: Normal
   - **Get Contents of URL**:
     - URL: `https://YOUR_VPS_IP:8100/transcribe`
     - Method: POST
     - Headers: `Authorization: Bearer YOUR_TOKEN`
     - Request Body: File → записанное аудио
   - **Get Dictionary Value**: key = `text`
   - **Copy to Clipboard**
   - **Show Notification**: показать результат

3. Добавь на Home Screen или назначь на Back Tap:
   Settings → Accessibility → Touch → Back Tap → Double Tap → Voice-Type

## Использование

- Двойной тап по задней крышке → говоришь → текст в буфере
- Открываешь любое приложение → вставляешь
