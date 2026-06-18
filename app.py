import base64
import io
import json
import wave
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from PIL import Image

st.set_page_config(layout="wide")

PROJECT_DIR = Path(__file__).resolve().parent
IMAGE_DIR = PROJECT_DIR / "Images"
AUDIO_EXTS = {".wav", ".waw", ".mp3", ".ogg", ".m4a"}
IMAGE_SECONDS = 3.0
DISPLAY_HEIGHT = 600


def find_audio_file(directory: Path):
    """Return the first supported audio file found in the project."""
    try:
        if directory.exists() and directory.is_dir():
            for path in sorted(directory.iterdir()):
                if path.is_file() and path.suffix.lower() in AUDIO_EXTS:
                    return path
    except Exception:
        pass

    try:
        for path in sorted(PROJECT_DIR.iterdir()):
            if path.is_file() and path.suffix.lower() in AUDIO_EXTS:
                return path
    except Exception:
        pass

    return None


def load_waveform(audio_path: Path, max_points: int = 4000):
    """Load a mono waveform from a WAV-like file using the stdlib wave module."""
    try:
        with wave.open(str(audio_path), "rb") as wf:
            samplerate = wf.getframerate()
            n_channels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            frames = wf.readframes(wf.getnframes())
    except Exception:
        return None

    if sampwidth == 1:
        data = np.frombuffer(frames, dtype=np.uint8).astype(np.float32)
        data = data - 128.0
    elif sampwidth == 2:
        data = np.frombuffer(frames, dtype=np.int16).astype(np.float32)
    else:
        return None

    if n_channels > 1:
        data = data.reshape(-1, n_channels).mean(axis=1)

    if len(data) > max_points:
        step = int(np.ceil(len(data) / max_points))
        data = data[::step]

    max_abs = float(np.max(np.abs(data))) if len(data) else 1.0
    if max_abs > 0:
        data = data / max_abs

    return samplerate, data.tolist()


def encode_image_as_base64(image_path: Path):
    img = Image.open(image_path).convert("RGB")
    aspect_ratio = img.width / img.height
    display_width = max(1, int(DISPLAY_HEIGHT * aspect_ratio))

    buffered = io.BytesIO()
    img.resize((display_width, DISPLAY_HEIGHT), Image.LANCZOS).save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode(), display_width


def audio_to_data_url(audio_path: Path):
    if not audio_path or not audio_path.exists():
        return ""

    ext = audio_path.suffix.lower()
    mime_types = {
        ".wav": "audio/wav",
        ".waw": "audio/wav",
        ".mp3": "audio/mpeg",
        ".ogg": "audio/ogg",
        ".m4a": "audio/mp4",
    }
    mime_type = mime_types.get(ext, "audio/wav")

    with open(audio_path, "rb") as f:
        audio_data = f.read()
    return f"data:{mime_type};base64,{base64.b64encode(audio_data).decode()}"


def load_images(df: pd.DataFrame):
    images = []
    widths = []
    for _, row in df.iterrows():
        image_path = IMAGE_DIR / str(row["image_path"])
        try:
            b64_img, display_width = encode_image_as_base64(image_path)
        except Exception:
            b64_img, display_width = "", 600
        images.append(b64_img)
        widths.append(display_width)
    return images, widths


# Data loading
csv_path = PROJECT_DIR / "test.csv"
df = pd.read_csv(csv_path, sep=";")
df.columns = df.columns.str.strip().str.lower()
df = df.sort_values("year").reset_index(drop=True)

if "current_idx" not in st.session_state:
    st.session_state.current_idx = 0

current_idx = int(st.session_state.current_idx)
current_idx = max(0, min(current_idx, len(df) - 1))
row = df.iloc[current_idx]

st.title("Yummy-Edible-Soundbites")

speed = st.sidebar.slider(
    "Playback Speed",
    0.25,
    5.0,
    1.0,
    0.25,
    help="Controls the audio playback rate",
)

# Preload assets
all_images_b64, image_widths = load_images(df)
audio_path = find_audio_file(PROJECT_DIR)
audio_data_url = audio_to_data_url(audio_path)
waveform = load_waveform(audio_path) if audio_path else None

if not audio_data_url:
    st.info("No audio file found in the project folder. Add a .wav file to enable synced playback.")
else:
    images_json = json.dumps(all_images_b64)
    widths_json = json.dumps(image_widths)
    years_json = json.dumps(df["year"].tolist())
    waveform_points = waveform[1] if waveform else []
    waveform_json = json.dumps(waveform_points)
    duration_seconds = (len(waveform_points) / waveform[0]) if waveform and waveform[0] else 0

    component_html = f"""
    <div style="font-family: sans-serif;">
      <style>
        .card {{
          border: 1px solid rgba(0,0,0,0.12);
          border-radius: 16px;
          padding: 16px;
          background: white;
          box-shadow: 0 8px 24px rgba(0,0,0,0.06);
        }}
          justify-content: space-between;
          gap: 12px;
          align-items: center;
          margin-bottom: 12px;
          color: #444;
          font-size: 14px;
        }}
        .viewer {{
          height: {DISPLAY_HEIGHT}px;
          display: flex;
          align-items: center;
          justify-content: center;
          overflow: hidden;
          border-radius: 12px;
          background: #f7f7f7;
        }}
        #display-image {{
          height: {DISPLAY_HEIGHT}px;
          width: auto;
          max-width: 100%;
          object-fit: contain;
          display: block;
          margin: 0 auto;
        }}
        audio {{
          width: 100%;
          margin-top: 12px;
        }}
        canvas {{
          width: 100%;
          height: 180px;
          display: block;
          margin-top: 16px;
          border-radius: 12px;
          background: #fafafa;
        }}
        .hint {{
          font-size: 13px;
          color: #666;
        }}
      </style>

      <div class="card">
        <div class="meta">
          <div>Current year: <strong id="year-label">{row['year']}</strong></div>
          <div class="hint">Press play on the audio player to advance images automatically every 3 seconds. You can adjust the pace of the playback by using the Playback Speed function.</div>
          <div style="height: 12px;"></div>
        </div>

        <div class="viewer">
          <img id="display-image" src="data:image/png;base64,{all_images_b64[current_idx] if all_images_b64 else ''}" alt="Current image" />
        </div>

        <audio id="player" controls preload="metadata">
          <source src="{audio_data_url}" />
          Your browser does not support the audio element.
        </audio>

        <canvas id="waveform"></canvas>
      </div>

      <script>
        const images = {images_json};
        const widths = {widths_json};
        const years = {years_json};
        const waveform = {waveform_json};
        const waveformDuration = {duration_seconds};
        const imageSeconds = {IMAGE_SECONDS};
        const startIdx = {current_idx};
        const speed = {speed};

        const player = document.getElementById('player');
        const imageEl = document.getElementById('display-image');
        const yearEl = document.getElementById('year-label');
        const canvas = document.getElementById('waveform');
        const ctx = canvas.getContext('2d');

        let currentIdx = startIdx;
        let timer = null;

        function resizeCanvas() {{
          const rect = canvas.getBoundingClientRect();
          const dpr = window.devicePixelRatio || 1;
          canvas.width = Math.max(1, Math.floor(rect.width * dpr));
          canvas.height = Math.max(1, Math.floor(rect.height * dpr));
          ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        }}

        function drawWaveform(currentTime) {{
          const rect = canvas.getBoundingClientRect();
          const width = rect.width;
          const height = rect.height;

          ctx.clearRect(0, 0, width, height);
          ctx.fillStyle = '#fafafa';
          ctx.fillRect(0, 0, width, height);

          if (!waveform || waveform.length < 2 || waveformDuration <= 0) {{
            ctx.fillStyle = '#666';
            ctx.font = '14px sans-serif';
            ctx.fillText('Waveform not available', 16, 24);
            return;
          }}

          ctx.strokeStyle = 'royalblue';
          ctx.lineWidth = 1;
          ctx.beginPath();
          for (let i = 0; i < waveform.length; i++) {{
            const x = (i / (waveform.length - 1)) * width;
            const y = height / 2 - waveform[i] * (height * 0.38);
            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
          }}
          ctx.stroke();

          const markerX = Math.max(0, Math.min(width, (currentTime / waveformDuration) * width));
          ctx.strokeStyle = 'red';
          ctx.lineWidth = 2;
          ctx.beginPath();
          ctx.moveTo(markerX, 0);
          ctx.lineTo(markerX, height);
          ctx.stroke();
        }}

        function updateDisplay() {{
          if (!player) return;

          const idx = Math.min(Math.floor(player.currentTime / imageSeconds), images.length - 1);
          if (idx !== currentIdx && images[idx]) {{
            currentIdx = idx;
            imageEl.src = 'data:image/png;base64,' + images[idx];
            imageEl.style.width = widths[idx] + 'px';
            if (yearEl) yearEl.textContent = years[idx];
          }}

          drawWaveform(player.currentTime || 0);
        }}

        function startLoop() {{
          if (timer) return;
          timer = setInterval(updateDisplay, 100);
        }}

        function stopLoop() {{
          if (!timer) return;
          clearInterval(timer);
          timer = null;
        }}

        player.playbackRate = speed;

        player.addEventListener('loadedmetadata', () => {{
          const startTime = Math.min(startIdx * imageSeconds, isFinite(player.duration) ? player.duration : startIdx * imageSeconds);
          try {{
            player.currentTime = startTime;
          }} catch (e) {{}}
          updateDisplay();
          drawWaveform(player.currentTime || 0);
        }});

        player.addEventListener('play', () => {{
          startLoop();
          updateDisplay();
        }});

        player.addEventListener('pause', stopLoop);
        player.addEventListener('seeking', updateDisplay);
        player.addEventListener('timeupdate', updateDisplay);

        window.addEventListener('resize', () => {{
          resizeCanvas();
          drawWaveform(player.currentTime || 0);
        }});

        resizeCanvas();
        updateDisplay();
        drawWaveform(player.currentTime || 0);
      </script>
    </div>
    """

if audio_data_url:
    components.html(component_html, height=1050, scrolling=False)

prev_col, next_col = st.columns(2)
with prev_col:
  if st.button("◀ Previous"):
    st.session_state.current_idx = max(0, current_idx - 1)
    st.rerun()
with next_col:
  if st.button("Next ▶"):
    st.session_state.current_idx = min(len(df) - 1, current_idx + 1)
    st.rerun()

st.markdown("<h3 style='font-size: 20pt;'>Timeline</h3>", unsafe_allow_html=True)
years = df["year"].tolist()
timeline_cols = st.columns(len(years))
for i, col in enumerate(timeline_cols):
    with col:
        if st.button(str(years[i]), key=f"year_{i}"):
            st.session_state.current_idx = i
            st.rerun()

st.info("WAV is supported. If your file is a .wav and the player still does not start, the browser controls above are the right place to click play.")
