"""
Robust Speech Engine: Multi-backend TTS/STT with Fallbacks
"""

import subprocess
import logging

try:
    import pyttsx3
except ImportError:
    pyttsx3 = None

try:
    import vosk
    import pyaudio
except ImportError:
    vosk = None
    pyaudio = None

try:
    import speech_recognition as sr
except ImportError:
    sr = None

class RobustTTS:
    def __init__(self):
        self.engine = None
        self.tts_backend = None
        self.logger = logging.getLogger("RobustTTS")
        self.select_backend()

    def select_backend(self):
        # Try espeak-ng (system), then pyttsx3, then festival
        if self._has_cmd("espeak-ng"):
            self.tts_backend = "espeak-ng"
        elif pyttsx3:
            self.tts_backend = "pyttsx3"
            self.engine = pyttsx3.init()
        elif self._has_cmd("festival"):
            self.tts_backend = "festival"
        else:
            self.tts_backend = None

    def _has_cmd(self, cmd):
        return subprocess.call(f"type {cmd}", shell=True,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE) == 0

    def speak(self, text):
        if self.tts_backend == "espeak-ng":
            subprocess.run(["espeak-ng", text])
        elif self.tts_backend == "pyttsx3" and self.engine:
            self.engine.say(text)
            self.engine.runAndWait()
        elif self.tts_backend == "festival":
            subprocess.run(["festival", "--tts"], input=text.encode())
        else:
            self.logger.error("No TTS backend available!")

class RobustSTT:
    def __init__(self, model_path="models/vosk/vosk-model-en"):
        self.stt_backend = None
        self.model_path = model_path
        self.logger = logging.getLogger("RobustSTT")
        self.select_backend()

    def select_backend(self):
        # Try Vosk (offline, recommended), then SpeechRecognition
        if vosk and pyaudio:
            self.stt_backend = "vosk"
        elif sr:
            self.stt_backend = "speech_recognition"
        else:
            self.stt_backend = None

    def recognize(self, duration=5):
        if self.stt_backend == "vosk":
            model = vosk.Model(self.model_path)
            rec = vosk.KaldiRecognizer(model, 16000)
            p = pyaudio.PyAudio()
            stream = p.open(format=pyaudio.paInt16, channels=1,
                            rate=16000, input=True, frames_per_buffer=4096)
            print("Say something...")
            for _ in range(int(16000 / 4096 * duration)):
                data = stream.read(4096)
                if rec.AcceptWaveform(data):
                    result = rec.Result()
                    stream.stop_stream()
                    stream.close()
                    p.terminate()
                    return result
            stream.stop_stream()
            stream.close()
            p.terminate()
            return ""
        elif self.stt_backend == "speech_recognition":
            r = sr.Recognizer()
            with sr.Microphone() as source:
                print("Say something...")
                audio = r.listen(source, phrase_time_limit=duration)
            try:
                return r.recognize_sphinx(audio)
            except sr.UnknownValueError:
                return ""
        else:
            self.logger.error("No STT backend available!")
            return ""

# Example usage:
if __name__ == "__main__":
    tts = RobustTTS()
    tts.speak("Hello! This is a robust TTS test.")

    stt = RobustSTT()
    print("Recognized:", stt.recognize())