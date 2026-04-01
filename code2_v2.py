import cv2
import mediapipe as mp
import time
import numpy as np
import random
import threading
import subprocess
import struct
import wave
import io
from scipy.spatial import distance as dist

# ---------------- GPIO (FIX UBUNTU + RPI5) ----------------
from gpiozero import Device, LED
from gpiozero.pins.lgpio import LGPIOFactory

Device.pin_factory = LGPIOFactory()

LED_PIN = 23

led = LED(LED_PIN)

# ---------------- OLED ----------------
from luma.core.interface.serial import i2c
from luma.oled.device import sh1106
from PIL import Image, ImageDraw

serial = i2c(port=1, address=0x3C)
device = sh1106(serial)

# ---------------- CONFIG ----------------
EAR_THRESHOLD = 0.23
CLOSED_TIME_THRESHOLD = 2.5
YAWN_THRESHOLD = 0.6
YAWN_WINDOW = 30
YAWN_COOLDOWN = 2
JOKE_COOLDOWN = 10

emotion_state = "normal"

# ---------------- AUDIO (MAX98357A vía ALSA) ----------------
tts_lock = threading.Lock()

# --- Beep ---
beep_active = False
beep_thread = None
beep_stop_event = threading.Event()

def _generate_beep_wav(frequency=1000, duration=0.5, sample_rate=44100):
    """Genera un WAV de tono sinusoidal en memoria."""
    n_samples = int(sample_rate * duration)
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        for i in range(n_samples):
            val = int(32767 * np.sin(2 * np.pi * frequency * i / sample_rate))
            wf.writeframes(struct.pack('<hh', val, val))  # estéreo L+R
    return buf.getvalue()

BEEP_WAV = _generate_beep_wav(frequency=1000, duration=0.4)

def _beep_loop(stop_event):
    """Reproduce el beep en loop hasta que stop_event se active."""
    while not stop_event.is_set():
        try:
            player = subprocess.Popen(
                ["aplay", "-q"],
                stdin=subprocess.PIPE,
                stderr=subprocess.DEVNULL
            )
            player.stdin.write(BEEP_WAV)
            player.stdin.close()
            player.wait()
        except Exception as e:
            print("ERROR BEEP:", e)
            break

def start_beep():
    global beep_active, beep_thread, beep_stop_event
    if beep_active:
        return
    beep_stop_event = threading.Event()
    beep_thread = threading.Thread(target=_beep_loop, args=(beep_stop_event,), daemon=True)
    beep_active = True
    beep_thread.start()

def stop_beep():
    global beep_active
    if not beep_active:
        return
    beep_stop_event.set()
    beep_active = False
    # Matar cualquier aplay activo del beep
    subprocess.run(["pkill", "-f", "aplay"], stderr=subprocess.DEVNULL)

# --- TTS ---
def speak_text(text):
    """Genera voz con espeak-ng y la reproduce por el MAX98357A."""
    with tts_lock:
        try:
            tts = subprocess.Popen(
                ["espeak-ng", "-v", "es", "-s", "120", "-a", "200", "--stdout", text],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL
            )
            player = subprocess.Popen(
                ["aplay", "-q"],
                stdin=tts.stdout,
                stderr=subprocess.DEVNULL
            )
            tts.stdout.close()
            player.wait()
            tts.wait()
        except Exception as e:
            print("ERROR AUDIO:", e)

# ---------------- CHISTES ----------------
jokes = [
    "¿Por qué los programadores confunden Halloween y Navidad? Porque OCT 31 es igual a DEC 25.",
    "¿Qué hace una abeja en el gimnasio? ¡Zum-ba!",
    "¿Por qué el libro de matemáticas estaba triste? Porque tenía muchos problemas.",
    "¿Qué le dice un bit al otro? Nos vemos en el bus.",
    "¿Por qué la computadora fue al doctor? Porque tenía un virus.",
    "¿Qué hace un pez programador? Nada, pero en código.",
    "¿Por qué el café fue a la policía? Porque lo asaltaron.",
    "¿Qué le dice una pared a otra? Nos vemos en la esquina."
]

last_joke_index = -1

def speak_joke():
    global last_joke_index
    idx = random.randint(0, len(jokes) - 1)
    while idx == last_joke_index:
        idx = random.randint(0, len(jokes) - 1)
    last_joke_index = idx
    speak_text("Oye, parece que estás cansado. Aquí va un chiste. " + jokes[idx])

def play_joke_async():
    threading.Thread(target=speak_joke, daemon=True).start()

# ---------------- DATOS CURIOSOS ----------------
fun_facts = [
    "¿Sabías que el cerebro humano puede generar suficiente electricidad para encender una bombilla pequeña?",
    "¿Sabías que parpadear limpia y lubrica tus ojos constantemente?",
    "¿Sabías que el bostezo ayuda a enfriar el cerebro?",
    "¿Sabías que los delfines duermen con un ojo abierto?",
    "¿Sabías que el corazón puede seguir latiendo fuera del cuerpo por unos segundos?",
    "¿Sabías que la fatiga reduce tus reflejos igual que el alcohol?",
    "¿Sabías que dormir bien mejora tu memoria y concentración?",
    "¿Sabías que el cuerpo humano tiene más de 600 músculos?"
]

last_fact_index = -1

def speak_fact():
    global last_fact_index
    idx = random.randint(0, len(fun_facts) - 1)
    while idx == last_fact_index:
        idx = random.randint(0, len(fun_facts) - 1)
    last_fact_index = idx
    speak_text("Bien hecho, has despertado. Aquí tienes un dato curioso. " + fun_facts[idx])

def play_fact_async():
    threading.Thread(target=speak_fact, daemon=True).start()

# ---------------- OLED CARA ----------------
def oled_face():
    global emotion_state
    eye_offset = 0
    direction = 1

    while True:
        img = Image.new("1", (128, 64))
        draw = ImageDraw.Draw(img)

        if emotion_state == "normal":
            draw.ellipse((32 + eye_offset, 18, 44 + eye_offset, 46), fill=255)
            draw.ellipse((84 + eye_offset, 18, 96 + eye_offset, 46), fill=255)
            draw.ellipse((35 + eye_offset, 24, 41 + eye_offset, 38), fill=0)
            draw.ellipse((87 + eye_offset, 24, 93 + eye_offset, 38), fill=0)
            draw.ellipse((37 + eye_offset, 26, 39 + eye_offset, 28), fill=255)
            draw.ellipse((89 + eye_offset, 26, 91 + eye_offset, 28), fill=255)
            draw.pieslice((38, 32, 90, 64), start=0, end=180, fill=255)
        elif emotion_state == "yawn":
            draw.ellipse((32, 18, 44, 46), fill=255)
            draw.ellipse((84, 18, 96, 46), fill=255)
            draw.ellipse((48, 34, 80, 62), fill=255)
        elif emotion_state == "sleepy":
            draw.line((30, 30, 50, 30), fill=255, width=3)
            draw.line((82, 30, 102, 30), fill=255, width=3)
            draw.line((48, 50, 80, 50), fill=255, width=2)
        elif emotion_state == "alert":
            draw.line((30, 28, 50, 34), fill=255, width=3)
            draw.line((82, 34, 102, 28), fill=255, width=3)
            draw.pieslice((38, 36, 90, 64), start=0, end=180, fill=255)

        device.display(img)

        if emotion_state == "normal":
            eye_offset += direction
            if abs(eye_offset) > 5:
                direction *= -1
        else:
            eye_offset = 0

        time.sleep(0.05)

threading.Thread(target=oled_face, daemon=True).start()

# ---------------- MEDIAPIPE ----------------
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    static_image_mode=False,
    max_num_faces=1,
    refine_landmarks=True
)

LEFT_EYE_IDX = [33, 160, 158, 133, 153, 144]
RIGHT_EYE_IDX = [362, 385, 387, 263, 373, 380]
MOUTH_IDX = [61, 291, 81, 178, 13, 14]

def eye_aspect_ratio(eye):
    A = dist.euclidean(eye[1], eye[5])
    B = dist.euclidean(eye[2], eye[4])
    C = dist.euclidean(eye[0], eye[3])
    return (A + B) / (2.0 * C)

def mouth_aspect_ratio(mouth):
    A = dist.euclidean(mouth[2], mouth[3])
    C = dist.euclidean(mouth[0], mouth[1])
    return A / C

# ---------------- VARIABLES ----------------
closed_start_time = None
yawn_times = []
last_yawn_time = 0
last_joke_trigger_time = 0
alarm_active = False

# ---------------- CÁMARA ----------------
cap = cv2.VideoCapture(0)
cap.set(3, 640)
cap.set(4, 480)

# ---------------- LOOP ----------------
while True:
    ret, frame = cap.read()
    if not ret:
        print("Error cámara")
        break

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(rgb)
    current_time = time.time()

    if results.multi_face_landmarks:
        led.on()

        face_landmarks = results.multi_face_landmarks[0]
        h, w, _ = frame.shape

        left_eye, right_eye, mouth = [], [], []

        for idx in LEFT_EYE_IDX:
            x = int(face_landmarks.landmark[idx].x * w)
            y = int(face_landmarks.landmark[idx].y * h)
            left_eye.append((x, y))

        for idx in RIGHT_EYE_IDX:
            x = int(face_landmarks.landmark[idx].x * w)
            y = int(face_landmarks.landmark[idx].y * h)
            right_eye.append((x, y))

        for idx in MOUTH_IDX:
            x = int(face_landmarks.landmark[idx].x * w)
            y = int(face_landmarks.landmark[idx].y * h)
            mouth.append((x, y))

        ear = (eye_aspect_ratio(left_eye) + eye_aspect_ratio(right_eye)) / 2.0
        mar = mouth_aspect_ratio(mouth)

        if ear < EAR_THRESHOLD:
            if closed_start_time is None:
                closed_start_time = current_time
                emotion_state = "sleepy"
            else:
                if current_time - closed_start_time > CLOSED_TIME_THRESHOLD:
                    start_beep()            # 🔔 Beep por MAX98357A
                    emotion_state = "alert"
                    alarm_active = True
                else:
                    emotion_state = "sleepy"
        else:
            if alarm_active:
                stop_beep()                 # ✅ Detener beep
                play_fact_async()           # 🔊 Voz por MAX98357A
                alarm_active = False

            closed_start_time = None
            emotion_state = "normal"

        if mar > YAWN_THRESHOLD:
            emotion_state = "yawn"
            if current_time - last_yawn_time > YAWN_COOLDOWN:
                yawn_times.append(current_time)
                last_yawn_time = current_time

        yawn_times = [t for t in yawn_times if current_time - t <= YAWN_WINDOW]

        if len(yawn_times) >= 3:
            if current_time - last_joke_trigger_time > JOKE_COOLDOWN:
                play_joke_async()
                last_joke_trigger_time = current_time
                yawn_times.clear()

    else:
        led.off()
        stop_beep()
        closed_start_time = None
        yawn_times.clear()
        emotion_state = "normal"

    if cv2.waitKey(1) & 0xFF == 27:
        break

cap.release()
stop_beep()
cv2.destroyAllWindows()
