"""
Voice-Type Mac Client
Правый Command -> запись (пилюля с волной внизу экрана) -> транскрибация -> в буфер.

Главный поток занят AppKit (overlay), клавиатура и сеть — в фоновых потоках.
Запуск с флагом --demo прокручивает все состояния пилюли без микрофона.
"""

import array
import io
import math
import os
import subprocess
import sys
import threading
import time
import wave

try:
    import pyaudio, requests, pyperclip
    from pynput import keyboard
    from pynput.keyboard import Key
    import overlay
except ImportError as e:
    print(f"Не хватает зависимости: {e}")
    print("pip install pyaudio requests pyperclip pynput pyobjc-framework-Cocoa")
    sys.exit(1)

def _load_env():
    """Подхватить .env рядом со скриптом: агент запускается без оболочки."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    os.environ.setdefault(key.strip(), value.strip())
    except FileNotFoundError:
        pass


_load_env()

API_URL = os.environ.get("VOICETYPE_URL", "http://YOUR_VPS_IP")
API_TOKEN = os.environ.get("VOICETYPE_TOKEN", "")

TRIGGER_KEY = Key.cmd_r

RATE, CHANNELS, CHUNK = 16000, 1, 1024
FORMAT = pyaudio.paInt16

# Нормализация громкости для волны: окно -60..0 dB -> 0..1 (как у VoiceInk)
DB_FLOOR = -60.0
LEVEL_SMOOTHING = 0.4  # EMA: чем меньше, тем плавнее волна

recording = False
audio_frames = []
pa = pyaudio.PyAudio()
stream = None
_smoothed_level = 0.0
_lock = threading.Lock()


def beep(sound_name="Tink"):
    subprocess.Popen(
        ["afplay", f"/System/Library/Sounds/{sound_name}.aiff"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )


def notify(title, text):
    subprocess.run([
        "osascript", "-e",
        f'display notification "{text}" with title "{title}"'
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _chunk_level(data):
    """RMS куска аудио -> 0..1 для высоты волны."""
    samples = array.array("h", data)
    if not samples:
        return 0.0
    rms = math.sqrt(sum(s * s for s in samples) / len(samples)) / 32768.0
    if rms <= 0:
        return 0.0
    db = 20 * math.log10(rms)
    norm = max(0.0, min(1.0, (db - DB_FLOOR) / -DB_FLOOR))
    return norm ** 0.7  # растянуть тихие уровни, чтобы волна была живой


def _audio_callback(data, frame_count, time_info, status):
    global _smoothed_level
    audio_frames.append(data)
    level = _chunk_level(data)
    _smoothed_level += LEVEL_SMOOTHING * (level - _smoothed_level)
    overlay.set_level(_smoothed_level)
    return (None, pyaudio.paContinue)


def start_recording():
    global recording, audio_frames, stream, _smoothed_level
    with _lock:
        if recording:
            return
        recording = True
    audio_frames = []
    _smoothed_level = 0.0
    try:
        stream = pa.open(format=FORMAT, channels=CHANNELS, rate=RATE,
                         input=True, frames_per_buffer=CHUNK,
                         stream_callback=_audio_callback)
    except Exception as e:
        with _lock:
            recording = False
        print(f"Микрофон недоступен: {e}")
        overlay.show_error("Микрофон недоступен")
        notify("Voice-Type", "Микрофон недоступен")
        return
    overlay.show_recording()
    beep("Tink")
    print("\U0001f399 Запись...")


def stop_and_transcribe():
    global recording, stream
    with _lock:
        if not recording:
            return
        recording = False
    time.sleep(0.1)
    if stream:
        stream.stop_stream()
        stream.close()
        stream = None
    if not audio_frames:
        print("Пустая запись")
        overlay.hide()
        return

    overlay.show_processing()
    beep("Pop")
    print("Отправка...")

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(pa.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b"".join(audio_frames))
    buf.seek(0)

    headers = {}
    if API_TOKEN:
        headers["Authorization"] = f"Bearer {API_TOKEN}"
    try:
        resp = requests.post(f"{API_URL}/transcribe",
                             files={"file": ("audio.wav", buf, "audio/wav")},
                             headers=headers, timeout=30)
        resp.raise_for_status()
        text = resp.json().get("text", "")
    except Exception as e:
        print(f"Ошибка: {e}")
        overlay.show_error("Нет связи с сервером")
        notify("Voice-Type", "Ошибка соединения")
        return

    if not text:
        print("Пустой результат")
        overlay.show_error("Не удалось распознать")
        notify("Voice-Type", "Не удалось распознать")
        return

    pyperclip.copy(text)
    print(f"OK: {text[:80]}...")
    overlay.show_done()
    beep("Glass")
    notify("Voice-Type", "Текст скопирован — нажми Cmd+V")


def on_press(key):
    if key == TRIGGER_KEY:
        start_recording()


def on_release(key):
    if key == TRIGGER_KEY:
        # сеть не должна блокировать поток клавиатуры
        threading.Thread(target=stop_and_transcribe, daemon=True).start()


def demo():
    """Прогон всех состояний пилюли без микрофона и клавиатуры."""
    overlay.show_recording()
    t0 = time.monotonic()
    while time.monotonic() - t0 < 4:
        # синтетический "голос": медленная огибающая поверх дрожания
        t = time.monotonic()
        level = 0.3 + 0.6 * abs(math.sin(t * 1.3)) * (0.7 + 0.3 * math.sin(t * 11))
        overlay.set_level(level)
        time.sleep(1 / 30)
    overlay.show_processing()
    time.sleep(3)
    overlay.show_done()
    time.sleep(2.5)
    overlay.show_error("Нет связи с сервером")
    time.sleep(3.5)
    print("Демо завершено")
    os._exit(0)


def main():
    print("Voice-Type")
    print(f"API: {API_URL}")
    print()
    print("Правый Cmd: зажми -> говори -> отпусти")
    print("Пилюля внизу экрана показывает запись и результат")
    print()

    # Диагностика и запрос разрешений: под launchd разрешения привязаны к
    # самому бинарю Python, поэтому просим их официальным системным диалогом.
    try:
        import Quartz
        listen_ok = bool(Quartz.CGPreflightListenEventAccess())
        print(f"Input Monitoring: {'OK' if listen_ok else 'НЕТ'}")
        if not listen_ok:
            Quartz.CGRequestListenEventAccess()  # системный диалог разрешения
    except Exception as e:
        print(f"Не удалось проверить разрешения: {e}")

    overlay.setup_app()

    if "--demo" in sys.argv:
        threading.Thread(target=demo, daemon=True).start()
    else:
        keyboard.Listener(on_press=on_press, on_release=on_release).start()

    overlay.run_forever()


if __name__ == "__main__":
    main()
