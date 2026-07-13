#!/bin/bash
# Voice-Type Mac: установка в один шаг.
# Копирует клиент в ~/Library/Application Support/VoiceType (launchd-агентам
# запрещён доступ к ~/Documents — TCC), ставит venv и включает автозапуск.
set -euo pipefail

SRC_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_DIR="$HOME/Library/Application Support/VoiceType"
PLIST_LABEL="com.voicetype.agent"
PLIST_DST="$HOME/Library/LaunchAgents/$PLIST_LABEL.plist"

if [ ! -f "$SRC_DIR/.env" ]; then
    echo "Нет файла .env — скопируй .env.example в .env и заполни:"
    echo "  VOICETYPE_URL=http://<адрес-твоего-сервера>"
    echo "  VOICETYPE_TOKEN=<токен>"
    exit 1
fi

mkdir -p "$APP_DIR"
cp "$SRC_DIR/voice_type.py" "$SRC_DIR/overlay.py" "$SRC_DIR/requirements.txt" "$APP_DIR/"
cp "$SRC_DIR/.env" "$APP_DIR/.env"
chmod 600 "$APP_DIR/.env"

# brew-питоны на этом Mac ломаются на ensurepip — берём python.org 3.13, если есть
PYTHON="/Library/Frameworks/Python.framework/Versions/3.13/bin/python3"
[ -x "$PYTHON" ] || PYTHON="python3"

cd "$APP_DIR"
if [ ! -d venv ]; then
    "$PYTHON" -m venv venv
fi
./venv/bin/pip install -q -r requirements.txt

# Мини-приложение VoiceType.app: macOS 26 не признаёт разрешения (Мониторинг
# ввода, Универсальный доступ) за голым интерпретатором под launchd — TCC
# выдаёт их только настоящему .app. Applet запускает python как дочерний
# процесс, и тот наследует разрешения приложения.
# НЕ пересобирать существующий бандл: новая ad-hoc подпись = новая личность
# для TCC, и выданные разрешения слетят.
if [ ! -d "$APP_DIR/VoiceType.app" ]; then
osacompile -o "$APP_DIR/VoiceType.app" - <<EOF
do shell script "cd " & quoted form of "$APP_DIR" & " && exec ./venv/bin/python3 -u voice_type.py"
EOF
INFO="$APP_DIR/VoiceType.app/Contents/Info.plist"
/usr/libexec/PlistBuddy -c "Set :CFBundleName VoiceType" "$INFO" 2>/dev/null \
    || /usr/libexec/PlistBuddy -c "Add :CFBundleName string VoiceType" "$INFO"
/usr/libexec/PlistBuddy -c "Set :CFBundleIdentifier com.voicetype.client" "$INFO" 2>/dev/null \
    || /usr/libexec/PlistBuddy -c "Add :CFBundleIdentifier string com.voicetype.client" "$INFO"
/usr/libexec/PlistBuddy -c "Add :LSUIElement bool true" "$INFO" 2>/dev/null || true
/usr/libexec/PlistBuddy -c "Add :NSMicrophoneUsageDescription string 'Запись голоса для транскрибации'" "$INFO" 2>/dev/null || true
codesign --force --deep -s - "$APP_DIR/VoiceType.app"
fi

# Собираем plist из шаблона: подставляем путь установки
mkdir -p "$HOME/Library/LaunchAgents"
sed "s|__CLIENT_DIR__|$APP_DIR|g" "$SRC_DIR/$PLIST_LABEL.plist" > "$PLIST_DST"

# Перезапуск агента (bootout молча падает, если агент ещё не был загружен)
launchctl bootout "gui/$(id -u)/$PLIST_LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST_DST"

sleep 2
if launchctl print "gui/$(id -u)/$PLIST_LABEL" | grep -q "state = running"; then
    echo "✓ Voice-Type запущен из $APP_DIR"
    echo "  Зажми правый Cmd и говори. Лог: /tmp/voicetype.log"
else
    echo "✗ Агент не запустился, смотри /tmp/voicetype.log"
    exit 1
fi
