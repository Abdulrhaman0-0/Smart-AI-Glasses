import cv2
import pyaudio
import wave
import keyboard
import os
import time
import asyncio
import edge_tts
import pygame
from dotenv import load_dotenv
from google import genai

# Load .env file
load_dotenv()

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

# Audio Recording Settings
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
    Input must be prefixed with a language code: 'ar|النص' / 'en|text' / 'fr|texte' etc.
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
    temp_file = "temp_speech.mp3"

    print(f"[TTS] lang={lang_code}, voice={voice.split('-')[2]}")
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
# Vision Pipeline (Enter Key)
# ==========================================
def process_vision():
    print("\n[Vision] 📸 Capturing...")
    image_path = "temp_vision.jpg"
    cap = cv2.VideoCapture(0)
    time.sleep(0.5)
    ret, frame = cap.read()
    cap.release()

    if not ret:
        print("[Error] Could not access camera.")
        speak_text("ar|عذراً، لا يمكن الوصول إلى الكاميرا")
        return

    cv2.imwrite(image_path, frame)

    print("[AI] Uploading and analyzing image...")
    success = False
    for attempt in range(3):
        try:
            sample_file = client.files.upload(file=image_path)
            prompt = "Extract any text in this image, translate it to Arabic. Return ONLY the Arabic translation. If no text, say 'No text found'."
            response = client.models.generate_content(
                model=MODEL_ID,
                contents=[sample_file, prompt]
            )
            client.files.delete(name=sample_file.name)
            result = response.text.strip()
            print(f"-> {result}")
            speak_text(f"ar|{result}")
            success = True
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
# Voice Pipeline (Space Key - Push to Talk)
# ==========================================
def start_recording():
    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
    frames = []

    print("\n[Voice] 🎙️ Recording... (Release Space to send)")
    while keyboard.is_pressed('space'):
        data = stream.read(CHUNK, exception_on_overflow=False)
        frames.append(data)

    stream.stop_stream()
    stream.close()
    p.terminate()

    if not frames:
        return None

    temp_audio = "temp_voice.wav"
    wf = wave.open(temp_audio, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()
    return temp_audio

def process_voice(audio_file_path):
    print("[AI] Uploading and thinking...")
    for attempt in range(3):
        try:
            sample_file = client.files.upload(file=audio_file_path)
            prompt = (
                "You are a highly intelligent and helpful AI assistant embedded in smart glasses. "
                "Listen to the user's audio, understand their query or command, and provide a helpful, conversational answer. "
                "You MUST respond in the EXACT SAME language the user spoke in — choose ONLY from: "
                "Arabic, English, French, German, Spanish, or Japanese. "
                "Prefix your response strictly with the 2-letter language code and a pipe symbol. "
                "Example if user asks about weather in Arabic: 'ar|الجو اليوم مشمس وجميل'. "
                "Example if user says hello in English: 'en|Hello! How can I help you today?'. "
                "Keep the response concise, natural, and directly address the user's input. No markdown, no emojis."
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

    if os.path.exists(audio_file_path):
        os.remove(audio_file_path)

# ==========================================
# Main Loop
# ==========================================
def main():
    print(">>> Smart AI Glasses - Laptop Dev Mode <<<")
    print("- Press 'Enter' → Vision (OCR + Arabic, Shakir voice)")
    print("- Hold 'Space'  → Universal Voice Assistant (Auto-Detect: 6 Languages)")
    print("- Press 'Esc'   → Quit")

    while True:
        if keyboard.is_pressed('enter'):
            process_vision()
            time.sleep(0.5)  # Debounce
        elif keyboard.is_pressed('space'):
            audio_file = start_recording()
            if audio_file:
                process_voice(audio_file)
        elif keyboard.is_pressed('esc'):
            print("\nShutting down...")
            break
        time.sleep(0.01)

if __name__ == "__main__":
    main()
