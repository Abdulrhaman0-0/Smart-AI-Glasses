# Smart AI Glasses — Powered by Raspberry Pi Zero 2 W & Gemini AI

> A wearable, AI-powered device that acts as a universal translator, text reader, and voice assistant — all from a pair of glasses. Built using Google Gemini, Edge-TTS, and Python.

---

## ✨ Features

- **📷 Vision Mode**: Captures the scene, extracts any text using OCR, and reads the Arabic translation aloud — instantly.
- **🎙️ Voice Assistant**: Push-to-talk multilingual assistant that detects your language and responds in the same language.
- **🌍 6-Language Auto-Detect**: Arabic, English, French, German, Spanish, and Japanese.
- **🔊 High-Quality TTS**: Powered by Microsoft Edge-TTS neural voices (no robot voice).
- **🤫 Headless Operation**: Runs silently on boot with no screen — speaks errors aloud so you always know the status.
- **🔋 Battery-Powered**: Custom 18650-based power circuit for portable use.

---

## 🛒 Bill of Materials (BOM)

### Core Hardware
| Component | Qty | Notes |
|---|---|---|
| Raspberry Pi Zero 2 W | 1 | With Wi-Fi & Bluetooth |
| microSD Card (32GB/64GB, Class 10/U1) | 1 | For the OS |
| USB microSD Card Reader | 1 | For flashing the OS |
| Pi Camera Module V1 / V1.3 (5MP) | 1 | — |
| 22-pin CSI Ribbon Cable (Pi Zero) | 1 | **Must be Pi Zero size** (not standard Pi size) |
| 2×20 GPIO Pin Header | 1 | Needs to be **soldered** to Pi Zero |
| Momentary Push Button | 2 | Any small tactile button |
| Female-to-Female Jumper Wires | 1 bundle | — |

### Audio
| Component | Qty | Notes |
|---|---|---|
| USB Sound Card (3.5mm Audio Adapter) | 1 | Pi Zero has no audio jack |
| Micro-USB OTG Adapter | 1 | To connect the USB Sound Card |
| 3.5mm Wired Headset with Microphone | 1 | — |

### Power Circuit
| Component | Qty | Notes |
|---|---|---|
| 18650 Lithium Battery 3.7V | 2 | — |
| 2-Cell 18650 Battery Holder | 1 | — |
| TP4056 Type-C Charging Module (with protection) | 1 | The one with `B+`/`B-`/`OUT+`/`OUT-` terminals |
| 5V Boost Step-Up Module (≥2A output) | 1 | e.g., MT3608 or similar |
| On/Off Switch | 1 | Between TP4056 OUT and Boost Module |
| Red/Black electrical wire | ~1m | — |
| Short Micro-USB power cable | 1 | To power the Pi Zero from the boost module |

### Assembly
| Component | Qty | Notes |
|---|---|---|
| 3D Printed Glasses Frame | 1 | Print from provided STL (or design your own) |
| Double-sided tape | — | For mounting PCBs |
| Zip ties | — | For cable management |
| Electrical tape | — | For insulating connections |

---

## ⚡ Circuit & Wiring Diagram

### Button Wiring (GPIO)

Both buttons use the Pi's internal **pull-up resistors** (handled by `gpiozero` automatically). No resistors needed.

| Button | Pi Zero GPIO Pin | Pi Zero GND Pin |
|---|---|---|
| Button 1 — **Vision** | GPIO 17 (Pin 11) | Any GND (e.g., Pin 9) |
| Button 2 — **Voice** | GPIO 27 (Pin 13) | Any GND (e.g., Pin 14) |

**Wiring:** One leg of the button → GPIO Pin. Other leg → GND Pin.

### Power Circuit Flow

```
[18650 x2 in Parallel (3.7V - Doubles the capacity)]
        |
        v
[TP4056 Module] <-- Type-C Charging port (to charge batteries)
  B+ / B-  (connect batteries here)
  OUT+ / OUT- (regulated, protected output)
        |
        v
[On/Off Switch]
        |
        v
[5V Boost Step-Up Module]
  IN+ / IN-  →  connects to Switch/TP4056 OUT
  OUT+ / OUT- (5V, ≥2A) →  connect to short Micro-USB cable
        |
        v
[Raspberry Pi Zero 2 W — Micro-USB Power Port]
```

> ⚠️ **Warning**: Always use a TP4056 module **with protection** (it has 4 output terminals). Modules without protection can cause battery fires or damage.

---

## 🖥️ Raspberry Pi Headless Setup

### Step 1: Flash the OS

1. Download **[Raspberry Pi Imager](https://www.raspberrypi.com/software/)**.
2. Select **OS**: `Raspberry Pi OS Lite (64-bit)` (no desktop needed).
3. Select your **microSD card**.
4. Click the **Edit Settings** (⚙️) icon:
   - Set **hostname** (e.g., `glasses`)
   - Set **username** and **password** (e.g., `pi` / `yourpassword`)
   - Configure **Wi-Fi**: enter your SSID and password
   - Enable **SSH** under the Services tab
5. Write the image.

### Step 2: First Boot & SSH

```bash
# From your laptop (after Pi connects to Wi-Fi):
ssh pi@glasses.local

# Or find the IP from your router admin page and use:
ssh pi@<PI_IP_ADDRESS>
```

### Step 3: Enable Camera & Audio

```bash
sudo raspi-config
```

- **Interface Options → Legacy Camera → Enable**
- **Interface Options → Audio** → if prompted, select output device
- Finish and **Reboot**.

---

## 🔧 Software Installation

### Step 1: Clone the Repository

```bash
cd ~
git clone https://github.com/YourUsername/gls.git
cd gls
```

### Step 2: Create a Python Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install System Dependencies

```bash
sudo apt-get update
sudo apt-get install -y python3-opencv portaudio19-dev libasound2-dev
```

### Step 4: Install Python Dependencies

```bash
pip install -r requirements.txt
```

### Step 5: Security & API Key Setup

#### 5a. Get Your Gemini API Key
1. Go to **[Google AI Studio](https://aistudio.google.com/app/apikey)**.
2. Click **"Create API Key"** and copy it.

#### 5b. Create Your `.env` File
The project reads the key from a `.env` file (never hardcoded). Run:

```bash
# On the Pi (or your laptop):
cp .env.example .env
nano .env
```

Edit the file to paste your key:
```env
GEMINI_API_KEY=AIzaSy...your_actual_key_here
```

Save and close (`Ctrl+X` → `Y` → `Enter`).

> [!IMPORTANT]
> The `.env` file is listed in `.gitignore` and will **never** be committed to Git. Never share it publicly.

#### 5c. Systemd Auto-Start: Pass the Key to the Service

When running as a systemd service (headless boot), the `.env` file is read automatically by `python-dotenv`. However, if the service still can't find the key, explicitly inject it into the service file:

In `/etc/systemd/system/glasses.service`, under `[Service]`, add:
```ini
Environment="GEMINI_API_KEY=AIzaSy...your_actual_key_here"
```

Then reload:
```bash
sudo systemctl daemon-reload
sudo systemctl restart glasses.service
```

---

## 🚀 Auto-Start on Boot (systemd)

### Step 1: Create the Service File

```bash
sudo nano /etc/systemd/system/glasses.service
```

Paste the following (adjust paths as needed):

```ini
[Unit]
Description=Smart AI Glasses Service
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/gls
ExecStart=/home/pi/gls/venv/bin/python /home/pi/gls/glasses_pi.py
Restart=on-failure
RestartSec=5
StandardOutput=append:/home/pi/gls/glasses.log
StandardError=append:/home/pi/gls/glasses.log

[Install]
WantedBy=multi-user.target
```

### Step 2: Enable and Start the Service

```bash
# Reload systemd to recognize the new service
sudo systemctl daemon-reload

# Enable the service to start on every boot
sudo systemctl enable glasses.service

# Start it now (without rebooting)
sudo systemctl start glasses.service

# Check status
sudo systemctl status glasses.service

# View live logs
tail -f /home/pi/gls/glasses.log
```

---

## 📁 Project File Structure

```
gls/
├── glasses_pi.py       # Production script for Raspberry Pi (GPIO buttons)
├── glasses_laptop.py   # Development/testing script (keyboard triggers)
├── Vision_Reader.py    # Standalone vision + dual TTS test script
├── voice_assistant.py  # Original standalone voice assistant script
├── test_audio.py       # TTS comparison test (Gemini vs Edge-TTS)
├── requirements.txt    # Python dependencies
├── .env.example        # Template — rename to .env and add your API key
├── .gitignore          # Protects secrets from being committed
├── setup_pi.md         # Quick reference Pi setup guide
└── README.md           # This file
```

---

## 🎮 Usage

### On Laptop (Development)
```bash
python glasses_laptop.py
```
| Key | Action |
|---|---|
| `Enter` | Vision mode: capture, OCR, translate, speak in Arabic |
| Hold `Space` | Voice mode: speak, AI responds in your language |
| `Esc` | Quit |

### On Raspberry Pi (Production)
The glasses start automatically on boot. Just turn the power switch on and wait ~20 seconds for the Pi to boot and connect to Wi-Fi. You will hear **"النظام جاهز"** (System Ready) when it's fully initialized.

- **Press Button 1 (GPIO 17)**: Vision / Text Translation (OCR → Arabic TTS)
- **Hold Button 1 (GPIO 17) for 5 seconds**: Safe Shutdown — gracefully powers off the Pi to protect the SD card
- **Hold Button 2 (GPIO 27)**: Voice Assistant — release the button to send the audio (works in 6 languages)

---

## 🔐 Security Note

> [!CAUTION]
> Never commit your real `.env` file to Git. It is already listed in `.gitignore` to prevent accidental exposure. Always use `.env.example` as the template and keep `.env` local only.

---

## 📜 License

This project was developed as a graduation project. Free to use and modify for educational purposes.
