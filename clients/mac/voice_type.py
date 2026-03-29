"""
Voice-Type Mac Client
Горячая клавиша -> запись -> транскрибация -> вставка текста.

Использование:
    python voice_type.py

Переменные окружения:
    VOICETYPE_URL    — URL API (default: http://YOUR_VPS_IP)
    VOICETYPE_TOKEN  — токен авторизации
"""

import os, io, sys, wave, threading, time

try:
    import pyaudio, requests, pyperclip
    from pynput import keyboard
    from pynput.keyboard import Key, Controller as KbController
except ImportError:
    print("pip install pyaudio requests pyperclip pynput")
    sys.exit(1)

API_URL = os.environ.get("VOICETYPE_URL", "http://YOUR_VPS_IP")
API_TOKEN = os.environ.get("VOICETYPE_TOKEN", "")
HOTKEY_STR = os.environ.get("VOICETYPE_HOTKEY", "<ctrl>+<shift>+space")

RATE, CHANNELS, CHUNK = 16000, 1, 1024
FORMAT = pyaudio.paInt16

recording = False
audio_frames = []
pa = pyaudio.PyAudio()
stream = None
kb = KbController()


def start_recording():
    global recording, audio_frames, stream
    if recording:
        return
    recording = True
    audio_frames = []
    stream = pa.open(format=FORMAT, channels=CHANNELS, rate=RATE,
                     input=True, frames_per_buffer=CHUNK)
    print("\U0001f399 Запись...")

    def _capture():
        while recording:
            try:
                audio_frames.append(stream.read(CHUNK, exception_on_overflow=False))
            except Exception:
                break
    threading.Thread(target=_capture, daemon=True).start()


def stop_and_transcribe():
    global recording, stream
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
        return

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
        return

    if not text:
        print("Пустой результат")
        return

    pyperclip.copy(text)
    print(f"OK: {text[:80]}...")

    paste_key = Key.cmd if sys.platform == "darwin" else Key.ctrl
    kb.press(paste_key)
    kb.press("v")
    kb.release("v")
    kb.release(paste_key)


def main():
    print(f"Voice-Type | API: {API_URL}")
    print(f"Горячая клавиша: {HOTKEY_STR}")
    print("Зажми -> говори -> отпусти -> текст вставится\n")

    hotkey = keyboard.HotKey(keyboard.HotKey.parse(HOTKEY_STR), start_recording)

    def on_press(key):
        try: hotkey.press(key)
        except: pass

    def on_release(key):
        try: hotkey.release(key)
        except: pass
        if recording:
            stop_and_transcribe()

    with keyboard.Listener(on_press=on_press, on_release=on_release) as l:
        l.join()


if __name__ == "__main__":
    main()
