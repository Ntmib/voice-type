"""
Voice-Type Mac Client
Правый Command -> запись -> транскрибация -> вставка текста.
"""

import os, io, sys, wave, threading, time, subprocess

try:
    import pyaudio, requests, pyperclip
    from pynput import keyboard
    from pynput.keyboard import Key
except ImportError:
    print("pip install pyaudio requests pyperclip pynput")
    sys.exit(1)

API_URL = os.environ.get("VOICETYPE_URL", "http://YOUR_VPS_IP")
API_TOKEN = os.environ.get("VOICETYPE_TOKEN", "")

TRIGGER_KEY = Key.cmd_r

RATE, CHANNELS, CHUNK = 16000, 1, 1024
FORMAT = pyaudio.paInt16

recording = False
audio_frames = []
pa = pyaudio.PyAudio()
stream = None


def beep(sound_name="Tink"):
    """Системный звук Mac для обратной связи."""
    subprocess.Popen(
        ["afplay", f"/System/Library/Sounds/{sound_name}.aiff"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )


def paste_via_applescript():
    """Вставка через AppleScript — работает везде."""
    subprocess.run([
        "osascript", "-e",
        'tell application "System Events" to keystroke "v" using command down'
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def notify(title, text):
    """Уведомление macOS."""
    subprocess.run([
        "osascript", "-e",
        f'display notification "{text}" with title "{title}"'
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def start_recording():
    global recording, audio_frames, stream
    if recording:
        return
    recording = True
    audio_frames = []
    stream = pa.open(format=FORMAT, channels=CHANNELS, rate=RATE,
                     input=True, frames_per_buffer=CHUNK)
    beep("Tink")
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
        notify("Voice-Type", "Ошибка соединения")
        return

    if not text:
        print("Пустой результат")
        notify("Voice-Type", "Не удалось распознать")
        return

    pyperclip.copy(text)
    print(f"OK: {text[:80]}...")

    time.sleep(0.2)
    paste_via_applescript()


def main():
    print("Voice-Type")
    print(f"API: {API_URL}")
    print()
    print("Правый Command: зажми -> говори -> отпусти -> текст вставится")
    print("Звук 'тинь' = запись началась")
    print("Звук 'поп' = запись закончилась, отправка")
    print()

    def on_press(key):
        if key == TRIGGER_KEY:
            start_recording()

    def on_release(key):
        if key == TRIGGER_KEY:
            stop_and_transcribe()

    with keyboard.Listener(on_press=on_press, on_release=on_release) as l:
        l.join()


if __name__ == "__main__":
    main()
