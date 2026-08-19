"""
Adaptive AI Lighting Director -- premium demo dashboard (Streamlit).

This UI is a presentation layer only. It calls the project's existing,
already-verified backend functions directly and displays their results --
it does not reimplement audio analysis, event detection, adaptive
scoring, learning, or STROBE cooldown logic. There is one authoritative
adaptive decision path in this project
(app.intelligence.lighting_decision.generate_lighting_sequence), the
same one app.audio.analyzer.main() and app.learning.live_feedback.main()
use, and this UI calls that same function -- no second decision engine
is created here.

Interactive DJ feedback in this UI is stored in a dedicated demo
profile/observation pair, never the real production files:
  data/dj_profiles/demo_dj.json
  data/dj_observations/demo_dj.json
data/dj_profiles/test_dj.json and data/dj_observations/test_dj.json
are never written by this UI.

Run with:
    streamlit run app/ui/streamlit_app.py
"""

import sys
import tempfile
import traceback
from pathlib import Path

# Make "app.*" importable regardless of the directory streamlit was
# launched from.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

from app.audio.analyzer import analyze_audio, detect_events
from app.learning.dj_profile import DJProfile
from app.observation.dj_observer import DJObserver
from app.intelligence.lighting_decision import (
    generate_lighting_sequence,
    get_confidence,
    ADAPTIVE_ACTIONS,
)


# ============================================================
# CONFIG -- demo data only. Real production files are never
# referenced for writing anywhere in this file.
# ============================================================

AUDIO_DIR = PROJECT_ROOT / "data" / "raw"
DEFAULT_AUDIO_PATH = AUDIO_DIR / "test_song.mp3"

UI_PROFILE_PATH = PROJECT_ROOT / "data" / "dj_profiles" / "demo_dj.json"
UI_OBSERVATIONS_PATH = PROJECT_ROOT / "data" / "dj_observations" / "demo_dj.json"

# Presentation-only metadata. None of this feeds back into any decision --
# it only controls how an already-decided action/context is *displayed*.
ACTION_META = {
    "PULSE":  {"glyph": "●", "color": "#57b4ff", "orb": "aild-orb-pulse"},
    "FLASH":  {"glyph": "◆", "color": "#ffd65a", "orb": "aild-orb-flash"},
    "STROBE": {"glyph": "✦", "color": "#d85aff", "orb": "aild-orb-strobe"},
    "DIM":    {"glyph": "◑", "color": "#c98a4b", "orb": "aild-orb-dim"},
}

CONTEXT_PHRASES = {
    "BEAT": "Beat detected",
    "ONSET": "New sound onset",
    "HIGH_ENERGY": "High-energy moment",
    "LOW_ENERGY": "Low-energy moment",
}

# Distinct from CONTEXT_PHRASES above: that one describes a single moment
# ("Low-energy moment"), this one is a plural noun phrase for sentences
# like "you like FLASH during ONSET moments" -- reusing CONTEXT_PHRASES
# there would read as "...during low-energy moment moments."
CONTEXT_FEEDBACK_LABEL = {
    "BEAT": "beat moments",
    "ONSET": "onset moments",
    "HIGH_ENERGY": "high-energy moments",
    "LOW_ENERGY": "low-energy moments",
}


def action_meta(action):
    return ACTION_META.get(action, ACTION_META["PULSE"])


def context_phrase(context):
    return CONTEXT_PHRASES.get(context, str(context).replace("_", " ").title())


def context_feedback_label(context):
    return CONTEXT_FEEDBACK_LABEL.get(
        context, f"{str(context).replace('_', ' ').lower()} moments"
    )


# ============================================================
# THEME
# ============================================================

def inject_theme():
    st.markdown(
        """
        <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header[data-testid="stHeader"] {background: transparent;}
        [data-testid="stToolbar"] {visibility: hidden;}
        [data-testid="stDecoration"] {display: none;}

        html, body, [class^="css"] {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI",
                Roboto, Helvetica, Arial, sans-serif;
        }

        .stApp {
            background: radial-gradient(circle at 15% -10%, #1b2033 0%, #0b0d14 55%, #05060a 100%);
        }

        .block-container {
            padding-top: 2.2rem;
            padding-bottom: 3rem;
            max-width: 1180px;
        }

        .aild-eyebrow {
            text-transform: uppercase;
            letter-spacing: 0.14em;
            font-size: 0.72rem;
            font-weight: 700;
            color: #8b8fa3;
            margin-bottom: 0.5rem;
        }

        .aild-hero-title {
            font-size: 2.7rem;
            font-weight: 800;
            letter-spacing: -0.02em;
            line-height: 1.15;
            background: linear-gradient(90deg, #ffffff 0%, #c3caff 60%, #9aa8ff 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem;
        }

        .aild-tagline {
            font-size: 1.08rem;
            color: #a7abc0;
            margin-bottom: 1.8rem;
        }

        .aild-card {
            background: rgba(255,255,255,0.035);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 18px;
            padding: 1.3rem 1.5rem;
            box-shadow: 0 8px 30px rgba(0,0,0,0.25);
        }

        .aild-step-card {
            text-align: center;
            padding: 1.1rem 0.8rem;
            font-size: 0.92rem;
            color: #cfd2e2;
        }

        .aild-stage {
            text-align: center;
            padding: 2.2rem 1rem 1.8rem 1rem;
        }
        .aild-stage-orb {
            width: 128px; height: 128px; border-radius: 50%;
            margin: 0 auto 1.1rem auto;
            display: flex; align-items: center; justify-content: center;
            font-size: 2.6rem; color: #ffffff;
        }
        @keyframes aild-breathe {
            0%, 100% { transform: scale(1); opacity: 0.92; }
            50% { transform: scale(1.06); opacity: 1; }
        }
        @keyframes aild-strobe {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.3; }
        }
        .aild-orb-pulse {
            background: radial-gradient(circle, #7fd4ff 0%, #2f6fbf 72%);
            box-shadow: 0 0 60px 12px rgba(87,180,255,0.45);
            animation: aild-breathe 2.4s ease-in-out infinite;
        }
        .aild-orb-flash {
            background: radial-gradient(circle, #fff6d8 0%, #e8b93a 72%);
            box-shadow: 0 0 70px 14px rgba(255,214,90,0.5);
            animation: aild-breathe 0.9s ease-in-out infinite;
        }
        .aild-orb-strobe {
            background: radial-gradient(circle, #ffffff 0%, #c85bff 72%);
            box-shadow: 0 0 80px 18px rgba(216,90,255,0.6);
            animation: aild-strobe 0.35s steps(2) infinite;
        }
        .aild-orb-dim {
            background: radial-gradient(circle, #8a5a26 0%, #3c220c 78%);
            box-shadow: 0 0 30px 6px rgba(160,90,30,0.3);
            animation: aild-breathe 4s ease-in-out infinite;
        }

        .aild-action-name {
            font-size: 2.3rem;
            font-weight: 800;
            letter-spacing: 0.01em;
            color: #f5f6fa;
        }
        .aild-context-phrase {
            color: #9aa0b8;
            font-size: 0.98rem;
            margin-top: 0.15rem;
        }

        .aild-stat-value {
            font-size: 1.85rem;
            font-weight: 700;
            color: #f2f3f7;
            line-height: 1.2;
        }
        .aild-stat-label {
            font-size: 0.75rem;
            color: #8b8fa3;
            text-transform: uppercase;
            letter-spacing: 0.07em;
        }

        .stButton > button {
            border-radius: 12px;
            font-weight: 600;
            border: 1px solid rgba(255,255,255,0.14);
            white-space: nowrap;
        }
        .stButton > button[kind="primary"] {
            background: linear-gradient(90deg, #6a5cff, #8f6bff);
            border: none;
        }

        .aild-chip {
            display: inline-flex; align-items: center; justify-content: center;
            min-width: 60px; padding: 0.45rem 0.65rem; margin-right: 0.4rem;
            margin-bottom: 0.4rem;
            border-radius: 10px; font-weight: 700; font-size: 0.78rem;
            background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.08);
            color: #a7abc0; letter-spacing: 0.02em;
        }
        .aild-chip-current {
            background: linear-gradient(90deg, #6a5cff, #8f6bff);
            color: white; border: none;
            box-shadow: 0 0 20px rgba(138,110,255,0.5);
        }

        .aild-bar-row { display:flex; align-items:center; margin-bottom: 0.6rem; }
        .aild-bar-label { width: 72px; font-weight:700; font-size:0.82rem; color:#c7cade; }
        .aild-bar-track {
            flex:1; height: 10px; background: rgba(255,255,255,0.06);
            border-radius: 6px; overflow:hidden; margin: 0 0.7rem;
        }
        .aild-bar-fill { height:100%; border-radius:6px; }
        .aild-bar-pct { width: 42px; text-align:right; font-size:0.8rem; color:#9aa0b8; }

        .aild-feed-item {
            font-size: 0.92rem; color: #c7cade; margin-bottom: 0.35rem;
        }

        input[type="checkbox"] { accent-color: #7d6bff; }

        .aild-hero-step {
            display: flex; align-items: center; gap: 0.8rem;
            padding: 0.55rem 0; font-size: 0.98rem; color: #c7cade;
        }
        .aild-hero-step-num {
            display: inline-flex; align-items: center; justify-content: center;
            width: 26px; height: 26px; border-radius: 50%; flex-shrink: 0;
            background: rgba(138,110,255,0.15); border: 1px solid rgba(138,110,255,0.4);
            color: #b9aeff; font-weight: 700; font-size: 0.8rem;
        }
        .aild-hero-note {
            color: #767b93; font-size: 0.85rem; margin-top: 0.7rem;
        }
        .aild-hero-orb-wrap {
            display: flex; align-items: center; justify-content: center;
            height: 100%; min-height: 260px;
        }
        .aild-hero-orb-big {
            width: 210px; height: 210px; font-size: 3.6rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def stat(col, value, label):
    col.markdown(
        f'<div class="aild-stat-value">{value}</div>'
        f'<div class="aild-stat-label">{label}</div>',
        unsafe_allow_html=True,
    )


# ============================================================
# CACHED / EXPENSIVE WORK
# ============================================================

@st.cache_data(show_spinner=False)
def cached_analyze_audio(path_str):
    return analyze_audio(path_str)


def load_or_create_profile():
    profile = DJProfile("Demo DJ")
    if UI_PROFILE_PATH.exists():
        profile.load(str(UI_PROFILE_PATH))
    return profile


def load_or_create_observer():
    observer = DJObserver("Demo DJ")
    if UI_OBSERVATIONS_PATH.exists():
        observer.load(str(UI_OBSERVATIONS_PATH))
    return observer


def rebuild_sequence():
    """
    Regenerate the adaptive lighting sequence from the current demo
    profile. Calls the SAME function the real pipeline uses -- no
    scoring logic lives in this file. Called once after analysis and
    again after every DJ feedback event, so later suggestions reflect
    what was just learned.
    """
    st.session_state.sequence = generate_lighting_sequence(
        st.session_state.events,
        st.session_state.profile,
    )


def run_analysis_pipeline(path_str):
    """
    The full, honest pipeline: analyze -> detect events -> generate the
    adaptive lighting sequence. Every status message below corresponds
    to a real step that is actually executing, not a fabricated
    progress percentage.
    """
    try:
        with st.status("Preparing your show...", expanded=True) as status:
            st.write("Listening to your track...")
            result = cached_analyze_audio(path_str)

            st.write("Detecting musical moments...")
            events = detect_events(result)

            st.write("Planning the lighting direction...")
            sequence = generate_lighting_sequence(events, st.session_state.profile)

            status.update(label="Show ready", state="complete", expanded=False)

        st.session_state.audio_result = result
        st.session_state.events = events
        st.session_state.sequence = sequence
        st.session_state.event_index = 0
        st.session_state.last_feedback_note = None
        st.session_state.changing = False
        st.session_state.analysis_error = None

    except Exception:
        st.session_state.analysis_error = traceback.format_exc()
        st.session_state.audio_result = None


# ============================================================
# SESSION STATE INIT
# ============================================================

_defaults = {
    "events": None,
    "sequence": None,
    "event_index": 0,
    "audio_result": None,
    "last_feedback_note": None,
    "changing": False,
    "analysis_error": None,
    "last_uploaded_name": None,
}
for key, value in _defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

if "profile" not in st.session_state:
    st.session_state.profile = load_or_create_profile()

if "observer" not in st.session_state:
    st.session_state.observer = load_or_create_observer()


# ============================================================
# PAGE
# ============================================================

st.set_page_config(
    page_title="Adaptive AI Lighting Director",
    page_icon="\U0001F39B",
    layout="wide",
)

inject_theme()


# ------------------------------------------------------------
# SIDEBAR -- track selection, developer view, reset
# ------------------------------------------------------------

with st.sidebar:
    st.markdown("### Track")

    uploaded = st.file_uploader(
        "Upload MP3", type=["mp3"], label_visibility="collapsed"
    )

    if uploaded is not None and uploaded.name != st.session_state.last_uploaded_name:
        tmp_path = Path(tempfile.gettempdir()) / uploaded.name
        with open(tmp_path, "wb") as f:
            f.write(uploaded.getbuffer())
        st.session_state.last_uploaded_name = uploaded.name
        run_analysis_pipeline(str(tmp_path))
        st.rerun()

    st.caption("or")

    if st.button("▶ Try Demo Track", width="stretch"):
        run_analysis_pipeline(str(DEFAULT_AUDIO_PATH))
        st.rerun()

    st.divider()

    dev_view = st.checkbox(
        "Developer view",
        value=False,
        help="Show raw scores, preferences, and full sequence data.",
    )

    st.divider()

    if st.button("Reset AI Learning", width="stretch"):
        for p in (UI_PROFILE_PATH, UI_OBSERVATIONS_PATH):
            if p.exists():
                p.unlink()
        st.session_state.profile = DJProfile("Demo DJ")
        st.session_state.observer = DJObserver("Demo DJ")
        if st.session_state.events is not None:
            rebuild_sequence()
        st.session_state.event_index = 0
        st.session_state.last_feedback_note = None
        st.session_state.changing = False
        st.success("AI learning reset.")

    st.caption(
        "Feedback here is saved to a private demo profile, never the "
        "real production data."
    )


# ------------------------------------------------------------
# ERROR STATE
# ------------------------------------------------------------

if st.session_state.analysis_error:
    st.error(
        "We couldn't analyze this track. It may be corrupted, silent, "
        "or an unsupported format."
    )
    with st.expander("Technical details"):
        st.code(st.session_state.analysis_error)
    st.stop()


# ------------------------------------------------------------
# EMPTY STATE / HERO
# ------------------------------------------------------------

if st.session_state.audio_result is None:
    st.markdown(
        '<div class="aild-eyebrow">Adaptive AI Lighting Director</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="aild-hero-title">AI that learns how you like your lights.</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="aild-tagline">Your music. Your style. AI-directed lighting.</div>',
        unsafe_allow_html=True,
    )

    hero_l, hero_r = st.columns([3, 2], gap="large")

    with hero_l:
        steps = [
            "Upload a track",
            "Let AI analyze it",
            "Watch the lighting director",
            "Teach it your style",
        ]
        for i, text in enumerate(steps, start=1):
            st.markdown(
                f'<div class="aild-hero-step">'
                f'<span class="aild-hero-step-num">{i}</span>{text}</div>',
                unsafe_allow_html=True,
            )

        st.write("")
        if st.button("▶ Try Demo Track", type="primary", key="hero_demo_btn", width="stretch"):
            run_analysis_pipeline(str(DEFAULT_AUDIO_PATH))
            st.rerun()
        st.markdown(
            '<div class="aild-hero-note">Or upload your own MP3 from the '
            '<b>Track</b> panel in the sidebar.</div>',
            unsafe_allow_html=True,
        )

    with hero_r:
        idle_orb = action_meta("PULSE")
        st.markdown(
            f"""
            <div class="aild-hero-orb-wrap">
                <div class="aild-stage-orb aild-hero-orb-big {idle_orb['orb']}">
                    {idle_orb['glyph']}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.stop()


# ------------------------------------------------------------
# DASHBOARD
# ------------------------------------------------------------

result = st.session_state.audio_result
events = st.session_state.events
sequence = st.session_state.sequence
profile = st.session_state.profile
observer = st.session_state.observer

top_l, top_r = st.columns([4, 1.3])
with top_l:
    st.markdown(
        '<div class="aild-eyebrow">Adaptive AI Lighting Director</div>',
        unsafe_allow_html=True,
    )
with top_r:
    if st.button("New Track", width="stretch"):
        st.session_state.audio_result = None
        st.rerun()

if not sequence:
    st.warning(
        "This track didn't produce any detectable musical moments. "
        "Try a different track."
    )
    st.stop()

# --- Music Analysis ---
st.markdown("#### Music Analysis")
c1, c2, c3, c4 = st.columns(4)
stat(c1, f"{result['bpm']:.0f}", "BPM")
energy_pct = min(result["average_energy"] * 100, 100)
stat(c2, f"{energy_pct:.0f}%", "Energy")
stat(c3, f"{result['duration']:.0f}s", "Duration")
stat(c4, f"{len(result['beats'])}", "Beats")

with st.expander("Advanced analysis"):
    a1, a2, a3, a4 = st.columns(4)
    a1.metric("Onsets", len(result["onsets"]))
    a2.metric("High-energy events", len(result["high_energy_events"]))
    a3.metric("Low-energy events", len(result["low_energy_events"]))
    a4.metric("Total detected events", len(events))
    st.caption(
        f"Lighting sequence length (post-dedup): {len(sequence)}  |  "
        f"Raw average RMS energy: {result['average_energy']:.4f}  |  "
        f"Spectral centroid: {result['spectral_centroid']:.1f} Hz"
    )

st.write("")

# Clamp index defensively (sequence length is stable across profile
# updates, but guard anyway).
st.session_state.event_index = min(st.session_state.event_index, len(sequence) - 1)
idx = st.session_state.event_index
current = sequence[idx]

context = current["context"]
ai_action = current["action"]
intensity = current["intensity"]
duration = current["duration"]
event_time = current["time"]
meta = action_meta(ai_action)

# get_confidence() reports confidence in whichever action the SIMPLE
# choose_action() engine would pick for this context -- which can
# occasionally differ from ai_action (chosen by the adaptive engine
# above, which also weighs energy/repetition/STROBE-cooldown). Showing
# that number here, next to a possibly-different action, would be
# misleading. Instead show a truthful, action-independent read on
# whether this context has been taught at all -- using only the
# existing get_context_preference() values, not a new metric.
has_context_learning = any(
    profile.get_context_preference(context, a) != 0.0 for a in ADAPTIVE_ACTIONS
)
decision_basis = (
    "Learned from your feedback" if has_context_learning else "Choosing based on this moment"
)

# --- AI Director stage ---
st.markdown("#### AI Director &mdash; Live Decision")

st.markdown(
    f"""
    <div class="aild-card aild-stage">
        <div class="aild-stage-orb {meta['orb']}">{meta['glyph']}</div>
        <div class="aild-action-name">{ai_action}</div>
        <div class="aild-context-phrase">
            {context_phrase(context)} &middot; {decision_basis}
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.write("")
s1, s2, s3 = st.columns(3)
stat(s1, f"{intensity * 100:.0f}%", "Intensity")
stat(s2, f"{duration:.2f}s", "Duration")
stat(s3, f"{event_time:.1f}s", "Track Time")

st.write("")

# --- Lighting show timeline ---
st.markdown("#### Lighting Show")
window = 4
start = max(0, idx - window)
end = min(len(sequence), idx + window + 1)
chips = []
for i in range(start, end):
    item = sequence[i]
    cls = "aild-chip aild-chip-current" if i == idx else "aild-chip"
    chips.append(f'<span class="{cls}">{item["action"]}</span>')
st.markdown("".join(chips), unsafe_allow_html=True)
st.progress((idx + 1) / len(sequence), text=f"Moment {idx + 1} of {len(sequence)}")

nav1, nav2, _ = st.columns([1, 1, 5])
with nav1:
    if st.button("‹ Previous", disabled=idx == 0, width="stretch"):
        st.session_state.event_index = max(0, idx - 1)
        st.session_state.changing = False
        st.rerun()
with nav2:
    if st.button("Next ›", disabled=idx >= len(sequence) - 1, width="stretch"):
        st.session_state.event_index = min(len(sequence) - 1, idx + 1)
        st.session_state.changing = False
        st.rerun()

st.write("")


# ------------------------------------------------------------
# DJ FEEDBACK
# ------------------------------------------------------------

def apply_feedback(dj_action):
    accepted = dj_action == ai_action

    label = context_feedback_label(context)

    if accepted:
        profile.observe(dj_action, rating=1.0, context=context)
        note = f"Got it. **{dj_action}** is now a bit more preferred for **{label}**."
    else:
        profile.observe(ai_action, rating=-1.0, context=context)
        profile.observe(dj_action, rating=1.0, context=context)
        note = f"Preference updated. You lean toward **{dj_action}** over **{ai_action}** for **{label}**."

    profile.save(str(UI_PROFILE_PATH))

    observer.record_observation(
        time=event_time,
        music_event=context,
        ai_action=ai_action,
        dj_action=dj_action,
        feedback=1.0 if accepted else -1.0,
    )
    observer.save(str(UI_OBSERVATIONS_PATH))

    st.session_state.last_feedback_note = note
    st.session_state.changing = False

    # Reflect the newly learned profile in future/remaining suggestions.
    rebuild_sequence()

    if st.session_state.event_index < len(st.session_state.sequence) - 1:
        st.session_state.event_index += 1


def skip_event():
    if st.session_state.event_index < len(st.session_state.sequence) - 1:
        st.session_state.event_index += 1
    st.session_state.changing = False
    st.session_state.last_feedback_note = None


st.markdown("#### DJ Feedback")
st.markdown(f"**AI chose {ai_action} for this moment. Do you like this?**")

k1, k2, k3, _ = st.columns([1, 1, 1, 3])
with k1:
    if st.button("Keep it", type="primary", key=f"keep_{idx}", width="stretch"):
        apply_feedback(ai_action)
        st.rerun()
with k2:
    if st.button("Change it", key=f"change_{idx}", width="stretch"):
        st.session_state.changing = True
with k3:
    if st.button("Skip", key=f"skip_{idx}", width="stretch"):
        skip_event()
        st.rerun()

if st.session_state.changing:
    st.caption("Choose what you'd actually want here:")
    choice_cols = st.columns(len(ADAPTIVE_ACTIONS))
    for i, action in enumerate(ADAPTIVE_ACTIONS):
        with choice_cols[i]:
            if st.button(action, key=f"choice_{action}_{idx}", width="stretch"):
                apply_feedback(action)
                st.rerun()

if st.session_state.last_feedback_note:
    st.success(st.session_state.last_feedback_note)

st.write("")
st.divider()


# ------------------------------------------------------------
# AI LEARNING
# ------------------------------------------------------------

st.markdown("#### AI Learning")
learn_col, feed_col = st.columns(2)

with learn_col:
    st.markdown("**Your Lighting Style**")
    if profile.observations == 0:
        st.caption(
            "Your AI director hasn't learned your style yet. "
            "Keep or change a few decisions to teach it."
        )
    else:
        for action in ADAPTIVE_ACTIONS:
            normalized = profile.get_normalized_preference(action)
            pct = (normalized + 1) / 2 * 100
            color = action_meta(action)["color"]
            st.markdown(
                f"""
                <div class="aild-bar-row">
                    <div class="aild-bar-label">{action}</div>
                    <div class="aild-bar-track">
                        <div class="aild-bar-fill" style="width:{pct:.0f}%; background:{color};"></div>
                    </div>
                    <div class="aild-bar-pct">{pct:.0f}%</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

with feed_col:
    st.markdown("**Recent Learning**")
    recent = list(reversed(observer.get_observations()[-5:]))
    if not recent:
        st.caption("No feedback recorded yet this session.")
    else:
        for obs in recent:
            phrase = context_phrase(obs["music_event"]).lower()
            if obs["ai_action"] == obs["dj_action"]:
                text = f"&check; You liked <b>{obs['dj_action']}</b> during a <b>{phrase}</b>"
            else:
                text = (
                    f"&#8635; You changed <b>{obs['ai_action']}</b> to "
                    f"<b>{obs['dj_action']}</b> during a <b>{phrase}</b>"
                )
            st.markdown(f'<div class="aild-feed-item">{text}</div>', unsafe_allow_html=True)

st.caption("Your AI director is adapting as you give feedback.")


# ------------------------------------------------------------
# DEVELOPER VIEW
# ------------------------------------------------------------

if dev_view:
    st.divider()
    st.markdown('<div class="aild-eyebrow">Developer View</div>', unsafe_allow_html=True)

    simple_engine_confidence = get_confidence(profile, context)
    st.caption(
        f"choose_action()'s confidence for this context: "
        f"{simple_engine_confidence * 100:.0f}%. This reflects the SIMPLE "
        f"decision engine's top pick, which can differ from the ADAPTIVE "
        f"engine's actual selection ({ai_action}) shown above -- that's "
        f"why the main view no longer pairs a percentage with the live "
        f"decision."
    )

    d1, d2 = st.columns(2)
    with d1:
        st.markdown("**Overall preferences**")
        st.dataframe(
            [
                {
                    "Action": action,
                    "Raw preference": profile.get_preference(action),
                    "Normalized (-1..1)": round(profile.get_normalized_preference(action), 3),
                }
                for action in ADAPTIVE_ACTIONS
            ],
            hide_index=True,
            width="stretch",
        )
    with d2:
        st.markdown(f"**Context preferences &mdash; {context}**")
        st.dataframe(
            [
                {
                    "Action": action,
                    "Raw preference": profile.get_context_preference(context, action),
                    "Normalized (-1..1)": round(
                        profile.get_normalized_context_preference(context, action), 3
                    ),
                }
                for action in ADAPTIVE_ACTIONS
            ],
            hide_index=True,
            width="stretch",
        )

    with st.expander("All learned contexts (raw)"):
        for ctx_name, actions in profile.context_preferences.items():
            st.markdown(f"**{ctx_name}**")
            st.dataframe(
                [{"Action": a, "Score": s} for a, s in actions.items()],
                hide_index=True,
                width="stretch",
            )

    with st.expander(f"Full lighting sequence ({len(sequence)} events)"):
        st.dataframe(
            [
                {
                    "Time (s)": item["time"],
                    "Context": item["context"],
                    "Action": item["action"],
                    "Intensity": item["intensity"],
                    "Duration (s)": item["duration"],
                }
                for item in sequence
            ],
            hide_index=True,
            width="stretch",
        )

    with st.expander(f"Raw observation log ({len(observer.get_observations())} entries)"):
        st.dataframe(observer.get_observations(), hide_index=True, width="stretch")
