# Прогресс: индикатор записи в стиле Wispr Flow

Ветка: claude/wishper-voice-recording-ui-ac7a4d (смержена в main локально)

- [x] Исследование Wispr Flow + VoiceInk (open source образец)
- [x] Спецификация docs/superpowers/specs/2026-07-13-recording-overlay-design.md
- [x] overlay.py — плавающая пилюля (NSPanel + волна из RMS)
- [x] voice_type.py — AppKit в главном потоке, pyaudio в callback-режиме
- [x] --demo режим, прогон без ошибок
- [x] Токен вынесен в .env, plist-шаблон исправлен
- [x] install.sh: установка в ~/Library/Application Support/VoiceType
      (launchd не пускают в ~/Documents), venv на python.org 3.13
- [x] Агент com.voicetype.agent установлен и запущен
- [ ] ЖДЁТ ДМИТРИЯ: включить Python в Настройки → Конфиденциальность →
      Универсальный доступ (иначе правый Cmd не ловится)
- [ ] ЖДЁТ ДМИТРИЯ: разрешить микрофон при первой записи
- [ ] Проверка живьём (обычное окно + fullscreen)
- [ ] Ротация VOICETYPE_TOKEN на VPS (старый засвечен в git-истории)
- [ ] git push (по команде Дмитрия)

Удалить этот файл по завершении.
