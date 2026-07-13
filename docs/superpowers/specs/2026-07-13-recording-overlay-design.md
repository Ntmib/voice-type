# Индикатор записи в стиле Wispr Flow — дизайн

Дата: 2026-07-13. Статус: согласован (вариант А — PyObjC в том же процессе).

## Задача

Mac-клиент voice-type даёт обратную связь только звуками. Нужен визуальный
индикатор как у Wispr Flow: плавающая «пилюля» внизу экрана с живой звуковой
волной, чтобы было видно, что запись идёт и когда она закончилась.
Обязательное требование: работает на Mac Дмитрия (M1 Pro, macOS 26.2)
«установил и работает» — автозапуск через launchd.

## Референсы

- Wispr Flow «Flow Bar»: пилюля низ-центр, состояния idle → recording
  (волна) → processing → вставка.
- VoiceInk (github.com/Beingpax/VoiceInk) — open source реализация:
  NSPanel(nonactivating, floating, clear) + 15 столбиков, высота =
  RMS × sin(t×8 + фаза) × буст к центру, RMS нормализуется в окне −60…0 dB.

## Архитектура

Один процесс, два файла в `clients/mac/`:

- `overlay.py` — вся работа с AppKit: NSPanel-пилюля + WaveView (отрисовка).
  Публичный API (потокобезопасный, через AppHelper.callAfter):
  `setup_app()`, `show_recording()`, `set_level(0..1)`, `show_processing()`,
  `show_done(text)`, `show_error(text)`, `hide()`, `run_forever()`.
- `voice_type.py` — логика: pynput-слушатель (фоновый поток, как штатно),
  pyaudio в callback-режиме (RMS на каждый chunk → set_level), отправка на
  сервер в отдельном потоке. Главный поток отдан AppKit
  (`AppHelper.runEventLoop()`), потому что AppKit работает только в нём.

## Пилюля

- NSPanel: borderless + nonactivatingPanel, level = NSStatusWindowLevel,
  `ignoresMouseEvents=True`, collectionBehavior = CanJoinAllSpaces |
  FullScreenAuxiliary (видна поверх fullscreen), `orderFrontRegardless()`
  (не крадёт фокус — иначе Cmd+V вставит не туда), фон clear.
- Позиция: центр по X, `visibleFrame.minY + 24`. Размер ~230×44.
- Вид: тёмная пилюля (чёрный, alpha 0.85), скругление = высота/2.

## Состояния

1. **hidden** — панель скрыта (idle-пилюлю не показываем, YAGNI).
2. **recording** — 15 белых столбиков (ширина 3, зазор 2, высота 4–28),
   высота = level × |sin(t×8 + i×0.5)| × центр-буст; level = EMA-сглаженный
   RMS (dB → 0..1 в окне −60…0, затем pow 0.7).
3. **processing** — столбики серые, бегущая волна независимо от микрофона.
4. **done** — текст «✓ Cmd+V», зелёный акцент, автоскрытие через 1.5 с.
5. **error** — текст ошибки, красный акцент, автоскрытие через 2.5 с.

Звуки Tink/Pop/Glass и уведомления остаются как были.

## Установка и запуск

- `--demo` флаг: прокрутка всех состояний с синтетическими уровнями без
  микрофона и клавиатуры — для проверки и скриншотов.
- `install.sh`: создать/обновить venv, поставить зависимости, записать токен
  в `.env` (права 600, в .gitignore), подставить абсолютные пути в plist,
  скопировать в `~/Library/LaunchAgents/`, `launchctl bootstrap`.
- plist: токен НЕ в plist (сейчас зашит — вынести, токен ротировать),
  путь — реальный `~/Documents/Projects/voice-type/clients/mac`.

## Ошибки

- Нет сети / сервер не ответил → состояние error + уведомление (как сейчас).
- Пустая запись → просто hide.
- Краш скрипта → KeepAlive в launchd перезапустит.

## Проверка

- `--demo` прогон + скриншот пилюли.
- Живой прогон: запись в обычном и fullscreen-приложении, обрыв сети.
- `launchctl list | grep voicetype` — агент жив после установки.
