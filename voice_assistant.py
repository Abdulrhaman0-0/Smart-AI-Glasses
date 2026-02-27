import pyaudio
import wave
import keyboard
from google import genai
from google.genai import types  # السطر الجديد المطلوب
from gtts import gTTS
import pygame
import os
import time

# ==========================================
# Initial Setup (API Setup)
# ==========================================
# Your API Key
GEMINI_API_KEY = "AIzaSyCWRu1eo4BrkvKv1-IM_5X7ccy6WxGogME"

# Initialize the genai client
client = genai.Client(api_key=GEMINI_API_KEY)

# Initialize audio library
pygame.mixer.init()

# ==========================================
# 1. Record Audio While Key is Pressed
# ==========================================
def record_while_pressed(filename="temp_record.wav"):
    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 44100
    
    p = pyaudio.PyAudio()
    
    print("\n[Voice] 🔴 Recording now... (Speak while holding 'Space')")
    
    # Wait until the user presses the space key
    while not keyboard.is_pressed('space'):
        time.sleep(0.05)
        if keyboard.is_pressed('q'):
            return None
            
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)
                    
    frames = []
    
    # Keep recording as long as the space key is held down
    while keyboard.is_pressed('space'):
        data = stream.read(CHUNK, exception_on_overflow=False)
        frames.append(data)
        
    print("-> ⏹️ Key released. Recording stopped.")
    
    stream.stop_stream()
    stream.close()
    p.terminate()
    
    # Check if frames were actually recorded
    if len(frames) == 0:
        print("-> Error: No audio frames captured. Try holding the key longer.")
        return None
        
    # Save the recorded audio
    wf = wave.open(filename, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()
    
    return filename

# ==========================================
# 2. Cloud Function (FAST Inline Processing)
# ==========================================
def process_audio_cloud(audio_file="temp_record.wav"):
    print("[AI] Sending data directly to Gemini...")
    try:
        # Read the audio file as raw bytes to avoid upload latency
        with open(audio_file, "rb") as f:
            audio_bytes = f.read()
            
        prompt = "You are a friendly, conversational AI companion built into a pair of smart glasses. Listen to the attached audio. Respond naturally, warmly, and concisely in English. Do not use emojis, lists, or markdown formatting."
        
        # استخدام الطريقة الصحيحة للنسخة الجديدة من المكتبة
        response = client.models.generate_content(
            model='gemini-2.5-flash', 
            contents=[
                types.Part.from_bytes(data=audio_bytes, mime_type='audio/wav'), 
                prompt
            ]
        )
        
        result_text = response.text.strip()
        print(f"-> AI Response:\n{result_text}")
        return result_text
        
    except Exception as e:
        print(f"-> AI Connection Error: {e}")
        return None

# ==========================================
# 3. Text-to-Speech (TTS) Function
# ==========================================
def speak_text(text, audio_file="ai_response.mp3"):
    if not text:
        return False
        
    print("[Audio] Converting AI response to speech and playing...")
    try:
        # Set lang='en' and tld='com' for an American English accent
        tts = gTTS(text=text, lang='en', tld='com', slow=False)
        tts.save(audio_file)
        
        pygame.mixer.music.load(audio_file)
        pygame.mixer.music.play()
        
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
            
        pygame.mixer.music.unload() 
        print("-> Audio playback finished.")
        return True
        
    except Exception as e:
        print(f"-> Audio Playback Error: {e}")
        return False

# ==========================================
# 4. Pipeline Function
# ==========================================
def run_voice_pipeline():
    record_file = "temp_record.wav"
    audio_file = "ai_response.mp3"
    
    # Step 1: Record while pressed
    recorded_file = record_while_pressed(record_file)
    if not recorded_file: 
        return False # User pressed 'q'
        
    # Step 2: Send audio directly to AI
    ai_response = process_audio_cloud(record_file)
    if not ai_response: return True
    
    # Step 3: TTS and Play
    speak_text(ai_response, audio_file=audio_file)
    
    # Clean up temporary files
    if os.path.exists(record_file):
        os.remove(record_file)
    if os.path.exists(audio_file):
        os.remove(audio_file)
        
    return True

# ==========================================
# Main Execution
# ==========================================
if __name__ == "__main__":
    print(">>> Smart Glasses - Voice Assistant Ready! <<<")
    print("\n" + "="*50)
    print("INSTRUCTIONS: ")
    print("- Press and HOLD the 'Space' key to talk.")
    print("- Release 'Space' to send your voice.")
    print("- Press 'q' to quit the program.")
    print("="*50)
    
    while True:               
        continue_running = run_voice_pipeline()
        if not continue_running:
            print("\nClosing system... Goodbye!")
            break
        print("-" * 50)