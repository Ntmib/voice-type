#!/bin/bash
# Voice-Type Mac: установка в один шаг.
# Ставит зависимости в venv, собирает launchd-агент из шаблона и запускает его.
set -euo pipefail

CLIENT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLIST_LABEL="com.voicetype.agent"
PLIST_DST="$HOME/Library/LaunchAgents/$PLIST_LABEL.plist"

cd "$CLIENT_DIR"

if [ ! -f .env ]; then
    echo "Нет файла .env — создай его рядом со скриптом:"
    echo "  VOICETYPE_TOKEN=<токен>"
    echo "  VOICETYPE_URL=http://YOUR_VPS_IP   # опционально"
    exit 1
fi
chmod 600 .env

if [ ! -d venv ]; then
    python3 -m venv venv
fi
./venv/bin/pip install -q -r requirements.txt

# Собираем plist из шаблона: подставляем реальный путь к клиенту
mkdir -p "$HOME/Library/LaunchAgents"
sed "s|__CLIENT_DIR__|$CLIENT_DIR|g" "$PLIST_LABEL.plist" > "$PLIST_DST"

# Перезапуск агента (bootout молча падает, если агент ещё не был загружен)
launchctl bootout "gui/$(id -u)/$PLIST_LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST_DST"

sleep 2
if launchctl print "gui/$(id -u)/$PLIST_LABEL" | grep -q "state = running"; then
    echo "✓ Voice-Type запущен. Зажми правый Cmd и говори."
    echo "  Лог: /tmp/voicetype.log"
else
    echo "✗ Агент не запустился, смотри /tmp/voicetype.log"
    exit 1
fi
