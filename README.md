# 😴 Sleepy — Drowsiness Detection Co-Pilot

> **A robot co-pilot capable of detecting drowsiness and keeping the driver awake.**  
> Built on Raspberry Pi 5 with real-time computer vision, facial landmark analysis, and multi-modal alerts.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Hardware Requirements](#hardware-requirements)
- [Prototype Gallery](#prototype-gallery)
- [System Setup](#system-setup)
  - [MAX98357A Audio Configuration](#max98357a-audio-configuration)
  - [Virtual Environment](#virtual-environment)
  - [Install Dependencies](#install-dependencies)
- [Audio Testing](#audio-testing)
- [Running the Program](#running-the-program)
- [Autostart on Boot (Headless)](#autostart-on-boot-headless)
- [Troubleshooting](#troubleshooting)
  - [GPIO Busy Error](#gpio-busy-error)
  - [Audio Issues](#audio-issues)
- [Project Structure](#project-structure)
- [Key Dependencies](#key-dependencies)
- [Authors](#authors)

---

## 🧠 Overview

**Sleepy** is an embedded co-pilot system designed to prevent drowsy driving accidents. It runs entirely on a Raspberry Pi 5 and uses a camera to monitor the driver's face in real time. When it detects prolonged eye closure or repeated yawning, it triggers audio and visual alerts to keep the driver alert and safe.

The system is fully autonomous — it boots and runs without a keyboard, mouse, or monitor, making it suitable for deployment inside a vehicle.

**How it works:**

1. A camera continuously captures the driver's face
2. MediaPipe extracts 468 facial landmarks per frame
3. Eye Aspect Ratio (EAR) and Mouth Aspect Ratio (MAR) are computed
4. If eyes are closed for more than 2.5 seconds → alarm triggers
5. If 3 or more yawns are detected in 30 seconds → TTS joke plays
6. An OLED display mirrors the driver's emotional state in real time

---

## ✨ Features

- 👁️ Real-time **eye aspect ratio (EAR)** detection for drowsiness
- 👄 **Yawn detection** via mouth aspect ratio (MAR)
- 🔔 **Beep alarm** through MAX98357A I2S DAC
- 🗣️ **Text-to-speech** alerts using `espeak-ng` with MBROLA voices
- 😊 **OLED face animations** (normal, sleepy, yawn, alert states)
- 💡 **LED indicator** — on when a face is detected
- 🎉 Random **fun facts** on wake-up and **jokes** on repeated yawning
- 🚗 **Fully headless** — runs automatically on power-up, no screen needed

---

## 🔧 Hardware Requirements

| Component | Details |
|-----------|---------|
| Raspberry Pi 5 | Ubuntu 24.04 |
| Camera | USB or CSI camera |
| OLED Display | SH1106 128×64 via I2C (address `0x3C`) |
| Audio Amplifier | MAX98357A via I2S |
| Speaker | 4–8 Ω passive speaker |
| LED | Connected to GPIO pin 23 |

---

## 🖼️ Prototype Gallery

### Physical Prototype

<!-- Add photos of the assembled hardware here -->
| | |
|---|---|
| ![Prototype front view](images/prototype_front.jpg) | ![Prototype side view](images/prototype_side.jpg) |
| *Front view* | *Side view* |

> 📸 _Place your prototype photos in the `/images` folder and update the paths above._

---

### 3D Model

<!-- Add renders or photos of the 3D printed enclosure here -->
| | |
|---|---|
| ![3D model render](images/3d_model_render.png) | ![3D printed enclosure](images/3d_printed.jpg) |
| *CAD render* | *Printed enclosure* |

> 📐 _Place your 3D model renders in the `/images` folder and update the paths above._

---

### System Diagram

<!-- Add a wiring or block diagram here -->
![System diagram](images/system_diagram.png)

> 🔌 _Add your circuit or block diagram image here._

---

## ⚙️ System Setup

### MAX98357A Audio Configuration

**1. Check available overlays:**
```bash
ls /boot/firmware/overlays/ | grep -i "max98357\|hifiberry\|i2s"
```

**2. Edit the boot config:**
```bash
sudo nano /boot/firmware/config.txt
```

Add at the end of the file (remove any previous `audremap` lines if present):
```
# I2S MAX98357
dtparam=i2s=on
dtoverlay=max98357a
```

**3. Reboot:**
```bash
sudo reboot
```

**4. Verify the audio card is detected:**
```bash
aplay -l
```

**5. Set volume and verify controls:**
```bash
amixer -c MAX98357A sset 'HiFi' 100% 2>/dev/null || amixer -c 0 controls
```

**6. Test with a sine wave tone:**
```bash
speaker-test -c 2 -t sine -f 1000 -D hw:MAX98357A
```

---

### Virtual Environment

**Create and activate the virtual environment:**
```bash
cd ~
python3 -m venv cv_env
source ~/cv_env/bin/activate
```

---

### Install Dependencies

**Install system packages first:**
```bash
sudo apt update
sudo apt install -y \
  python3-dev \
  python3-pip \
  libatlas-base-dev \
  libjpeg-dev \
  libopenblas-dev \
  i2c-tools \
  espeak-ng \
  mbrola \
  mbrola-us1 \
  mbrola-us2 \
  mbrola-us3 \
  mbrola-en1 \
  mbrola-es1 \
  mbrola-es2
```

**Install Python packages inside the virtual environment:**
```bash
source ~/cv_env/bin/activate

pip install \
  opencv-python \
  mediapipe \
  numpy \
  scipy \
  gpiozero \
  lgpio \
  luma.oled \
  Pillow
```

---

## 🔊 Audio Testing

**Test espeak-ng TTS directly from terminal:**
```bash
# English (American female — us1)
espeak-ng -v mb-us1 -s 120 "Hello, I am your driving assistant." --stdout | aplay -q

# English (American male — us2)
espeak-ng -v mb-us2 -s 120 "Hello, I am your driving assistant." --stdout | aplay -q

# English (American male — us3)
espeak-ng -v mb-us3 -s 120 "Hello, I am your driving assistant." --stdout | aplay -q

# Spanish (female — es2, most stable on RPi)
espeak-ng -v mb-es2 -s 110 "Hola, soy tu asistente de conducción." --stdout | aplay -q
```

**Test using a temporary WAV file (recommended — avoids pipe glitches on RPi):**
```bash
espeak-ng -v mb-us3 -s 110 -w /tmp/test.wav "Hello, I am your driving assistant."
aplay -q /tmp/test.wav
```

**Quick Python TTS test:**
```bash
python3 -c "
import subprocess
tmp = '/tmp/tts_out.wav'
subprocess.run(['espeak-ng', '-v', 'mb-us3', '-s', '110', '-w', tmp, 'Hello, I am your driving assistant.'])
subprocess.run(['aplay', '-q', tmp])
"
```

---

## ▶️ Running the Program

```bash
source ~/cv_env/bin/activate
cd ~/Documents/sleepy
sudo ~/cv_env/bin/python3 code2_v2.py
```

> **Note:** `sudo` is required for GPIO and I2C access.

Press `ESC` to stop the program.

---

## 🚀 Autostart on Boot (Headless)

This setup uses **systemd** to run the program automatically every time the Raspberry Pi powers on — no keyboard or monitor needed.

**1. Create the service file:**
```bash
sudo nano /etc/systemd/system/sleepy.service
```

**2. Paste the following content:**
```ini
[Unit]
Description=Sleepy Driver Monitor
After=network.target

[Service]
ExecStartPre=/bin/sleep 60
ExecStart=/home/utec/cv_env/bin/python3 /home/utec/Documents/sleepy/code2_v2.py
WorkingDirectory=/home/utec/Documents/sleepy
StandardOutput=journal
StandardError=journal
Restart=always
RestartSec=10
User=utec
Environment=DISPLAY=:0
Environment=HOME=/home/utec

[Install]
WantedBy=multi-user.target
```

> `ExecStartPre=/bin/sleep 60` waits 60 seconds after boot before launching, giving the RPi time to fully initialize the camera, GPIO, I2C, and audio hardware.

**3. Enable and start the service:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable sleepy.service
sudo systemctl start sleepy.service
```

**4. Verify it is running:**
```bash
sudo systemctl status sleepy.service
```

**Useful service management commands:**
```bash
# View live logs
sudo journalctl -u sleepy.service -f

# View all logs
sudo journalctl -u sleepy.service --no-pager

# Stop the service
sudo systemctl stop sleepy.service

# Restart the service
sudo systemctl restart sleepy.service

# Disable autostart
sudo systemctl disable sleepy.service
```

---

## 🛠️ Troubleshooting

### GPIO Busy Error

If you see a `GPIOBusy` or `Device or resource busy` error, a previous Python process is still holding the GPIO pin.

**1. Find the conflicting process:**
```bash
ps aux | grep python
```

Example output:
```
utec  2607  ... python3 code2_v2.py
utec  2608  ... python3 code2_v2.py
```

**2. Kill the processes by PID:**
```bash
sudo kill -9 2607 2608 2609
```

**3. Or kill all Python processes at once:**
```bash
sudo pkill -f python3
```

**4. Run again:**
```bash
sudo ~/cv_env/bin/python3 code2_v2.py
```

---

### Audio Issues

**No sound output:**
```bash
# Check that the card is recognized
aplay -l

# Check that the overlay loaded correctly
dmesg | grep -i max98357
```

**Choppy or glitchy TTS audio:**

This is a known issue with mbrola voices on Raspberry Pi when using pipes. The solution is to write to a temporary WAV file first:

```python
def speak_text(text):
    with tts_lock:
        try:
            tmp = "/tmp/tts_out.wav"
            subprocess.run(
                ["espeak-ng", "-v", "mb-us3", "-s", "110", "-w", tmp, text],
                stderr=subprocess.DEVNULL
            )
            subprocess.run(
                ["aplay", "-q", tmp],
                stderr=subprocess.DEVNULL
            )
        except Exception as e:
            print("ERROR AUDIO:", e)
```

**Kill a stuck `aplay` process:**
```bash
sudo pkill -f aplay
```

---

## 📁 Project Structure

```
sleepy/
├── code2_v2.py           # Main program
├── README.md             # This file
└── images/               # Photos and diagrams
    ├── prototype_front.jpg
    ├── prototype_side.jpg
    ├── 3d_model_render.png
    ├── 3d_printed.jpg
    └── system_diagram.png
```

---

## 📦 Key Dependencies

| Package | Purpose |
|---------|---------|
| `opencv-python` | Camera capture and frame processing |
| `mediapipe` | 468-point facial landmark detection |
| `scipy` | Euclidean distance for EAR/MAR computation |
| `gpiozero` + `lgpio` | GPIO LED control on RPi 5 |
| `luma.oled` | SH1106 OLED display driver |
| `Pillow` | Image drawing for OLED face animations |
| `espeak-ng` + `mbrola` | Text-to-speech engine with natural voices |
| `numpy` | Beep waveform generation |

---

## 👤 Authors

**Luis David Barahona Valdivieso**  
Ingeniería Electrónica  
Universidad de Ingeniería y Tecnología — UTEC, Lima, Perú

---

> 🤖 *This project was developed with the assistance of **Claude Sonnet 4.6**, an AI model created by [Anthropic](https://www.anthropic.com).*
