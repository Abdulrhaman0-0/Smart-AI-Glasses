# Raspberry Pi Setup for Smart AI Glasses

Follow these steps to set up your Raspberry Pi Zero 2 W for the Smart AI Glasses project.

## 1. Enable Camera Interface
Run the following command on your Pi:
```bash
sudo raspi-config
```
Navigate to **Interface Options** -> **Camera** and select **Yes** to enable it. Reboot the Pi.

*Note: If using the newer Bullseye/Bookworm OS, you might need to use `libcamera` or enable legacy support in `raspi-config`.*

## 2. Install Dependencies
Run these commands to install system libraries and Python packages:
```bash
sudo apt-get update
sudo apt-get install -y python3-opencv portaudio19-dev libasound2-dev
pip3 install -r requirements.txt
```

## 3. Run on Boot (systemd)
Create a service file to ensure the glasses start automatically:
```bash
sudo nano /etc/systemd/system/glasses.service
```

Paste the following:
```ini
[Unit]
Description=Smart AI Glasses Service
After=network.target

[Service]
ExecStart=/usr/bin/python3 /home/pi/gls/glasses_pi.py
WorkingDirectory=/home/pi/gls
StandardOutput=inherit
StandardError=inherit
Restart=always
User=pi

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl enable glasses.service
sudo systemctl start glasses.service
```

## 4. Hardware Wiring
- **Vision Button**: Connect between GPIO 17 and GND.
- **Voice Button**: Connect between GPIO 27 and GND.
- `gpiozero` assumes an internal pull-up resistor by default.
