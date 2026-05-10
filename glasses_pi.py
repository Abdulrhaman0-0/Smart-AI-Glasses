import cv2
import pyaudio
import wave
import os
import time
import asyncio
import signal
import edge_tts
import pygame
from dotenv import load_dotenv
from google import genai
from gpiozero import Button

# Load API key from .env file
load_dotenv()

# Store the latest translated text from the camera
last_seen_text = ""

# ==========================================
# API Key Rotation Setup
# ==========================================
_raw_keys = os.getenv("GEMINI_API_KEYS", "")
API_KEYS = [k.strip() for k in _raw_keys.split(",") if k.strip()]
if not API_KEYS:
    print("[FATAL] GEMINI_API_KEYS not set. Add comma-separated keys to your .env file.")
    exit(1)

current_key_index = 0
client = genai.Client(api_key=API_KEYS[current_key_index])
print(f"[Keys] Loaded {len(API_KEYS)} API key(s). Starting with key #1.")
MODEL_ID = "gemini-2.5-flash"

# GPIO Pins
VISION_PIN = 17
VOICE_PIN = 27

# Audio Settings
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100

# Edge-TTS Voice IDs (6 Languages)
VOICE_AR = "ar-EG-ShakirNeural"   # Arabic  - Male  Egyptian
VOICE_EN = "en-US-GuyNeural"      # English - Male  US
VOICE_FR = "fr-FR-HenriNeural"    # French  - Male  France
VOICE_DE = "de-DE-KillianNeural"  # German  - Male  Germany
VOICE_ES = "es-ES-AlvaroNeural"   # Spanish - Male  Spain
VOICE_JA = "ja-JP-NanamiNeural"   # Japanese- Female Japan

VOICE_MAP = {
    'ar': VOICE_AR,
    'en': VOICE_EN,
    'fr': VOICE_FR,
    'de': VOICE_DE,
    'es': VOICE_ES,
    'ja': VOICE_JA,
}

# Initialize Hardware Buttons
vision_button = Button(VISION_PIN, hold_time=5)  # 5s hold triggers safe shutdown
voice_button = Button(VOICE_PIN)                 # Short press = PTT, no hold needed

# Initialize Pygame for playback
pygame.mixer.init()

# ==========================================
# API Key Rotation
# ==========================================
def rotate_api_key():
    """Rotate to the next API key in the list (loops back to 0 when all exhausted)."""
    global current_key_index, client
    current_key_index = (current_key_index + 1) % len(API_KEYS)
    client = genai.Client(api_key=API_KEYS[current_key_index])
    print(f"[Rotate] Switched to API key #{current_key_index + 1}")

# ==========================================
# TTS Function (edge-tts)
# ==========================================
async def _generate_speech(text, voice, filepath):
    communicate = edge_tts.Communicate(text=text, voice=voice)
    await communicate.save(filepath)

def speak_text(text):
    """Speaks text using edge-tts.
    Input must be prefixed: 'ar|النص' / 'en|text' / 'fr|texte' etc.
    If no valid prefix found, defaults to English.
    """
    if not text or "No text found" in text:
        return

    # Always split on the first '|' to cleanly separate prefix from content
    if "|" in text:
        lang_code, clean_text = text.split("|", 1)
        lang_code = lang_code.strip().lower()
        clean_text = clean_text.strip()
    else:
        lang_code = 'en'
        clean_text = text.strip()

    voice = VOICE_MAP.get(lang_code, VOICE_EN)
    temp_file = "/tmp/temp_speech.mp3"

    try:
        asyncio.run(_generate_speech(clean_text, voice, temp_file))
        pygame.mixer.music.load(temp_file)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
        pygame.mixer.music.unload()
    except Exception as e:
        print(f"[Error] TTS: {e}")
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)

# ==========================================
# Vision Pipeline (GPIO 17)
# ==========================================
def run_vision():
    print("[Vision] Triggered...")
    image_path = "/tmp/temp_vision.jpg"
    import os
    # Use native OS camera tool to save RAM
    capture_cmd = f"rpicam-jpeg -o {image_path} --width 640 --height 480 -t 1000 > /dev/null 2>&1"
    exit_code = os.system(capture_cmd)

    if exit_code != 0 or not os.path.exists(image_path):
        print("[Error] Camera capture failed.")
        speak_text("ar|عذراً، لا يمكن الوصول إلى الكاميرا")
        return

    for attempt in range(3):
        try:
            print("[AI] Uploading image...")
            sample_file = client.files.upload(file=image_path)
            prompt = "Extract text, translate to Arabic. Return ONLY Arabic or 'No text found'."
            response = client.models.generate_content(
                model=MODEL_ID,
                contents=[sample_file, prompt]
            )
            client.files.delete(name=sample_file.name)
            result = response.text.strip()
            
            global last_seen_text
            last_seen_text = result
            
            speak_text(f"ar|{result}")
            break
        except Exception as e:
            if "429" in str(e):
                print(f"[Quota] Rate limit hit. Switching API key... (Attempt {attempt+1}/3)")
                rotate_api_key()
                # Loop continues immediately with the new key — no sleep needed
            else:
                print(f"[Error] Vision AI: {e}")
                speak_text("ar|خطأ في الاتصال بالذكاء الاصطناعي")
                break

    if os.path.exists(image_path):
        os.remove(image_path)

# ==========================================
# Voice Pipeline (GPIO 27 - Push to Talk)
# ==========================================
def record_and_process_voice():
    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
    frames = []

    print("[Voice] Listening...")
    while voice_button.is_pressed:
        data = stream.read(CHUNK, exception_on_overflow=False)
        frames.append(data)

    stream.stop_stream()
    stream.close()
    p.terminate()

    if len(frames) < 5:
        return  # Too short

    print("[Voice] Processing...")
    audio_path = "/tmp/temp_voice.wav"
    wf = wave.open(audio_path, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()

    for attempt in range(3):
        try:
            print("[AI] Uploading audio...")
            sample_file = client.files.upload(file=audio_path)
            global last_seen_text
            prompt = (
                "You are Smarty, a highly intelligent and friendly AI assistant built into smart glasses. "
                "You have two modes of operation:\n"
                "1. GRADUATION PROJECT MODE (Priority):\n"
                "- If asked about 'Talk about us', 'Who are we?', or the students/team:\n"
                "  * English response: \"You're in specific education college at kafrelshiekh university, you're studying computer teacher program in English.\"\n"
                "  * Arabic response: \"أنتم في كلية التربية النوعية بجامعة كفر الشيخ، تدرسون في برنامج معلم الحاسب باللغة الإنجليزية.\"\n"
                "- If asked about 'Code Verse' or 'تيم كود فيرس':\n"
                "  * Arabic response: \"تيم كود فيرس هما تيم في الفرقه الرابعه ، وانا مشروع تخرجكم الخاص بقسم معلم حاسب باللغة الإنجليزية، كلية التربية النوعية ، جامعة كفر الشيخ.\"\n"
                "  * English response: \"Code Verse is a team of seniors, and I am their graduation project for the Computer Teacher Program in English, Faculty of Specific Education, Kafrelsheikh University.\"\n"
                "- If asked exactly 'Who are you?', 'What is your job?', or 'انت مين؟':\n"
                "  * English response: \"I am Smarty, your smart glasses. I have a camera, mic, and speaker. I can see what you see and help you with learning difficulties.\"\n"
                "  * Arabic response: \"انا سمارتي، نظارتك السمارت مربوط بسماعه و مايك وكاميرا، اقدر اشوف من خلال الكاميرا اللي مربوطة بيا واسمع سؤالك من خلال المايك واجاوبك، وانتم صممتوني علشان اقدر اساعد الاشخاص اللي عندها صعوبات في التعلم.\"\n"
                "\n"
                "2. GENERAL AI MODE (Fallback):\n"
                "- For general greetings (e.g., 'How are you?', 'Hello', 'أهلاً'), questions, or any other topic, respond naturally and creatively in the user's language as a general AI assistant.\n"
                f"- If asked about what they are looking at, use this recently captured text: '{last_seen_text}'.\n"
                "\n"
                "CONSTRAINTS:\n"
                "- You MUST respond in the EXACT SAME language the user spoke.\n"
                "- Prefix response with: 'lang_code|' (e.g., 'ar|...', 'en|...').\n"
                "- Keep it concise, conversational, and do not use markdown or emojis."
            )
            response = client.models.generate_content(
                model=MODEL_ID,
                contents=[sample_file, prompt]
            )
            client.files.delete(name=sample_file.name)
            result = response.text.strip()
            print(f"-> AI: {result}")
            speak_text(result)  # Language auto-detected from prefix
            break
        except Exception as e:
            if "429" in str(e):
                print(f"[Quota] Rate limit hit. Switching API key... (Attempt {attempt+1}/3)")
                rotate_api_key()
                # Loop continues immediately with the new key
            else:
                print(f"[Error] Voice AI: {e}")
                speak_text("en|Connection error, please check internet")
                break

    if os.path.exists(audio_path):
        os.remove(audio_path)

# ==========================================
# Safe Shutdown (Hold Voice Button 5s)
# ==========================================
def safe_shutdown():
    """Called when the voice button is held for 5+ seconds."""
    print("[Shutdown] 5s hold detected. Shutting down safely...")
    speak_text("en|Shutting down the system gracefully. Please wait.")
    import subprocess
    subprocess.run(["sudo", "poweroff"])

# ==========================================
# Main Loop (Interrupt Driven)
# ==========================================
def main():
    print(">>> Smart AI Glasses - Pi Production Mode <<<")
    print("- Press GPIO 17        -> Vision (OCR + Arabic, Shakir voice)")
    print("- Hold GPIO 17 (5s)    -> Safe Shutdown")
    print("- Hold GPIO 27         -> Universal Voice Assistant (Auto-Detect: 6 Languages)")

    vision_button.when_pressed = run_vision
    vision_button.when_held = safe_shutdown      # 5s hold on Vision button
    voice_button.when_pressed = record_and_process_voice  # Normal PTT

    print("[System] Ready. Announcing...")
    speak_text("ar|النظام جاهز")

    signal.pause()

if __name__ == "__main__":
    main()
