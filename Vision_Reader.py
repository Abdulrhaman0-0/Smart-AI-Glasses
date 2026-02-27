import cv2
from google import genai
from gtts import gTTS
import pygame
import os
import time

# ==========================================
# Initial Setup (API Setup)
# ==========================================
# Your API Key
GEMINI_API_KEY = "AIzaSyCWRu1eo4BrkvKv1-IM_5X7ccy6WxGogME"

# Initialize the new genai client
client = genai.Client(api_key=GEMINI_API_KEY)

# Initialize audio library
pygame.mixer.init()

# ==========================================
# 1. Image Capture Function
# ==========================================
def capture_image(image_path="temp_capture.jpg"):
    print("[1] Opening camera and capturing image...")
    try:
        cap = cv2.VideoCapture(0) # 0 means default laptop camera
        
        # Give the camera a second to adjust lighting and focus
        time.sleep(1) 
        ret, frame = cap.read()
        cap.release()
        
        if ret:
            cv2.imwrite(image_path, frame)
            print("-> Image captured successfully.")
            return True
        else:
            print("-> Error: Could not capture image.")
            return False
            
    except Exception as e:
        print(f"-> Camera Error: {e}")
        return False

# ==========================================
# 2. Cloud Function (OCR + Translation via Gemini)
# ==========================================
def process_image_cloud(image_path="temp_capture.jpg"):
    print("[2] Sending image to AI for OCR and translation...")
    try:
        # Upload image using the new SDK
        sample_file = client.files.upload(file=image_path)
        
        # Prompt for Gemini 
        prompt = "Extract any text found in this image, then translate it into Arabic. Return ONLY the translated Arabic text without any additions, introductions, or explanations. If no text is found at all, return exactly the phrase: 'No text found'."
        
        # Request response using the new SDK syntax
        response = client.models.generate_content(
            model='gemini-2.5-flash', 
            contents=[sample_file, prompt]
        )
        
        # Delete image from Google servers immediately for privacy
        client.files.delete(name=sample_file.name)
        
        result_text = response.text.strip()
        print(f"-> Cloud Response:\n{result_text}")
        return result_text
        
    except Exception as e:
        print(f"-> AI Connection Error: {e}")
        return None

# ==========================================
# 3. Text-to-Speech (TTS) Function
# ==========================================
def speak_text(text, lang='ar', audio_file="output_audio.mp3"):
    # Ignore speech if no text was found
    if "No text found" in text or not text:
        print("-> No valid text to speak.")
        return False
        
    print("[3] Converting text to speech and playing...")
    try:
        # Convert text to audio
        tts = gTTS(text=text, lang=lang, slow=False)
        tts.save(audio_file)
        
        # Play audio file
        pygame.mixer.music.load(audio_file)
        pygame.mixer.music.play()
        
        # Pause program until audio finishes
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
            
        # Unload audio file to allow deletion
        pygame.mixer.music.unload() 
        print("-> Audio playback finished.")
        return True
        
    except Exception as e:
        print(f"-> Audio Playback Error: {e}")
        return False

# ==========================================
# 4. Pipeline Function (Button 1)
# ==========================================
def run_button_1_pipeline():
    image_file = "temp_capture.jpg"
    audio_file = "output_audio.mp3"
    
    # Execute steps in order
    if not capture_image(image_file): return
    
    result_text = process_image_cloud(image_file)
    if not result_text: return
    
    speak_text(result_text, lang='ar', audio_file=audio_file)
    
    # Clean up temporary files
    if os.path.exists(image_file):
        os.remove(image_file)
    if os.path.exists(audio_file):
        os.remove(audio_file)

# ==========================================
# Main Execution
# ==========================================
if __name__ == "__main__":
    print(">>> Smart Glasses System Ready! <<<")
    print("\n" + "="*50)
    choice = input("Press 'Enter' to capture & translate (or type 'q' to quit): ")
    
    if choice.lower() == 'q':
        print("Closing system... Goodbye!")
    else:
        print("-" * 50)
        run_button_1_pipeline()
        print("-> Task completed. Closing system... Goodbye!")