# Прогресс: индикатор записи в стиле Wispr Flow

Ветка: claude/wishper-voice-recording-ui-ac7a4d

- [x] Исследование Wispr Flow + VoiceInk (open source образец)
- [x] Разведка окружения Mac: venv python 3.13, PyObjC уже установлен, launchd-агент НЕ установлен, путь в plist неверный, токен зашит в plist
- [ ] Спецификация docs/superpowers/specs/2026-07-13-recording-overlay-design.md
- [ ] overlay.py — плавающая пилюля (NSPanel + волна из RMS)
- [ ] voice_type.py — перестройка: AppKit в главном потоке, pyaudio в callback-режиме
- [ ] --demo режим для проверки без микрофона
- [ ] Локальный прогон + скриншот
- [ ] Починка plist: правильный путь, токен в .env (.gitignore)
- [ ] install.sh: venv + launchd в один шаг
- [ ] Установка на Mac, проверка что агент жив
- [ ] README обновить
- [ ] Merge в main (локально, без push), напомнить про ротацию токена

Удалить этот файл по завершении.
