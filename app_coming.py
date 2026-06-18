import streamlit as st
import pandas as pd
import json
from pathlib import Path
import time # Import time for sleep

st.set_page_config(layout="wide")

IMAGE_DIR = "/content/Images/" # Corrected IMAGE_DIR to point to /content/Images/
AUDIO_DIR = "audio"

df = pd.read_csv("test.csv") # Ensure this reloads the updated test.csv
df = df.sort_values("year").reset_index(drop=True)

st.title("Yummy-Edible-Soundbites")

if "current_idx" not in st.session_state:
    st.session_state.current_idx = 0
if "is_playing" not in st.session_state: # New state for slideshow
    st.session_state.is_playing = False

idx = st.session_state.current_idx
row = df.iloc[idx]

# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------

speed = st.sidebar.slider(
    "Playback Speed",
    0.25,
    5.0,
    1.0,
    0.25
)

# New slider for slideshow interval
sideshow_interval = st.sidebar.slider(
    "Slideshow Interval (seconds)",
    1, # Minimum interval
    10, # Maximum interval
    3 # Default interval
)

# --------------------------------------------------
# IMAGE VIEW
# --------------------------------------------------

col1, col2 = st.columns([3,1])

with col1:

    st.image(
        str(Path(IMAGE_DIR) / row["image_path"]),
        width='stretch'
    )

with col2:

    st.subheader("Current Motif")

    st.write(f"Year: {row['year']}") # Corrected SyntaxError


# --------------------------------------------------
# AUDIO
# --------------------------------------------------

continuous_audio_file = str(Path(AUDIO_DIR)/"your_long_audio_file.waw")

# Pass is_playing state to JavaScript for audio control
is_playing_js = "true" if st.session_state.is_playing else "false"

st.markdown(
    f"""
    <audio id="player" controls loop> <!-- Removed autoplay attribute -->
      <source src="{continuous_audio_file}">
    </audio>

    <script>
    const player = document.getElementById("player");
    player.playbackRate = {speed};

    // Control audio play/pause based on Streamlit's is_playing state
    if ({is_playing_js}) {{
        if (player.paused) {{
            player.play().catch(e => console.log("Audio play failed:", e));
        }}
    }} else {{
        if (!player.paused) {{
            player.pause();
        }}
    }}
    </script>
    """,
    unsafe_allow_html=True
)

# --------------------------------------------------
# TIMELINE
# --------------------------------------------------

st.markdown("## Timeline")

years = list(df["year"])

timeline_cols = st.columns(len(years))

for i, c in enumerate(timeline_cols):

    with c:

        if st.button(
            str(years[i]),
            key=f"year_{i}"
        ):
            st.session_state.current_idx = i
            st.session_state.is_playing = False # Pause slideshow if user manually navigates
            st.rerun()

# --------------------------------------------------
# PREVIOUS / NEXT (Re-inserted)
# --------------------------------------------------
st.markdown("### Manual Navigation")
c1, c2 = st.columns(2)

with c1:

    if st.button("◀ Previous"):

        st.session_state.current_idx = max(
            0,
            idx - 1
        )
        st.session_state.is_playing = False # Pause slideshow if user manually navigates
        st.rerun()

with c2:

    if st.button("Next ▶"):

        st.session_state.current_idx = min(
            len(df)-1,
            idx + 1
        )
        st.session_state.is_playing = False # Pause slideshow if user manually navigates
        st.rerun()

# --------------------------------------------------
# SLIDESHOW CONTROLS
# --------------------------------------------------
st.markdown("### Slideshow Controls")
col_play, col_pause = st.columns(2)

with col_play:
    if st.button("▶ Play Slideshow", disabled=st.session_state.is_playing):
        st.session_state.is_playing = True
        st.rerun()

with col_pause:
    if st.button("❚❚ Pause Slideshow", disabled=not st.session_state.is_playing):
        st.session_state.is_playing = False
        st.rerun()

# Slideshow auto-advance logic
if st.session_state.is_playing:
    # Advance index
    next_idx = idx + 1
    if next_idx >= len(df):
        next_idx = 0 # Loop back to beginning
    st.session_state.current_idx = next_idx

    # Wait for the interval before rerunning
    time.sleep(sideshow_interval)
    st.rerun()


# --------------------------------------------------
# Plotly Events (Remains the same)
# --------------------------------------------------
from streamlit_plotly_events import plotly_events
import plotly.graph_objects as go

fig = go.Figure()

fig.add_trace(
    go.Scatter(
        x=df["year"],
        y=[1]*len(df),
        mode="markers",
        marker_size=15
    )
)

selected = plotly_events(
    fig,
    click_event=True
)
