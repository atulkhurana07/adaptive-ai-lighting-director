# app/audio/analyzer.py

import os
import sys
import numpy as np
import librosa

from app.learning.dj_profile import DJProfile
from app.intelligence.lighting_decision import (
    choose_action,
    get_confidence,
    generate_lighting_sequence as generate_adaptive_lighting_sequence,
)


# ============================================================
# CONFIG
# ============================================================

AUDIO_PATH = "data/raw/test_song.mp3"
PROFILE_PATH = "data/dj_profiles/test_dj.json"

ACTIONS = ["PULSE", "FLASH", "STROBE", "DIM", "IDLE"]


# ============================================================
# AUDIO ANALYSIS
# ============================================================

def analyze_audio(file_path):
    """
    Analyze an audio file and return all useful information.

    Returns:
        dict containing:
        bpm
        duration
        average_energy
        spectral_centroid
        beats
        onsets
        high_energy_events
        low_energy_events
    """

    print("Loading audio...")

    y, sr = librosa.load(
        file_path,
        sr=None,
        mono=True
    )

    print("Analyzing music...")

    # --------------------------------------------------------
    # BASIC INFORMATION
    # --------------------------------------------------------

    duration = librosa.get_duration(
        y=y,
        sr=sr
    )

    # --------------------------------------------------------
    # BPM / BEATS
    # --------------------------------------------------------

    tempo, beat_frames = librosa.beat.beat_track(
        y=y,
        sr=sr
    )

    # librosa may return numpy array for tempo
    if isinstance(tempo, np.ndarray):
        tempo = float(tempo.flatten()[0])
    else:
        tempo = float(tempo)

    beat_times = librosa.frames_to_time(
        beat_frames,
        sr=sr
    )

    # --------------------------------------------------------
    # ONSETS
    # --------------------------------------------------------

    onset_frames = librosa.onset.onset_detect(
        y=y,
        sr=sr,
        backtrack=False
    )

    onset_times = librosa.frames_to_time(
        onset_frames,
        sr=sr
    )

    # --------------------------------------------------------
    # ENERGY
    # --------------------------------------------------------

    rms = librosa.feature.rms(
        y=y
    )[0]

    rms_times = librosa.frames_to_time(
        np.arange(len(rms)),
        sr=sr
    )

    average_energy = float(
        np.mean(rms)
    )

    # --------------------------------------------------------
    # SPECTRAL CENTROID
    # --------------------------------------------------------

    centroid = librosa.feature.spectral_centroid(
        y=y,
        sr=sr
    )[0]

    spectral_centroid = float(
        np.mean(centroid)
    )

    # --------------------------------------------------------
    # ENERGY THRESHOLDS
    # --------------------------------------------------------

    high_threshold = float(
        np.percentile(rms, 75)
    )

    low_threshold = float(
        np.percentile(rms, 25)
    )

    high_energy_events = []
    low_energy_events = []

    for i, energy in enumerate(rms):

        time = float(rms_times[i])

        if energy >= high_threshold:
            high_energy_events.append(time)

        elif energy <= low_threshold:
            low_energy_events.append(time)

    # --------------------------------------------------------
    # REMOVE VERY CLOSE ENERGY EVENTS
    # --------------------------------------------------------

    high_energy_events = reduce_events(
        high_energy_events,
        min_gap=0.20
    )

    low_energy_events = reduce_events(
        low_energy_events,
        min_gap=0.20
    )

    # --------------------------------------------------------
    # RESULT
    # --------------------------------------------------------

    return {
        "bpm": tempo,
        "duration": float(duration),

        "average_energy": average_energy,
        "spectral_centroid": spectral_centroid,

        "beats": [float(x) for x in beat_times],
        "onsets": [float(x) for x in onset_times],

        "high_energy_events": high_energy_events,
        "low_energy_events": low_energy_events,
    }


# ============================================================
# REMOVE EVENTS THAT ARE TOO CLOSE
# ============================================================

def reduce_events(events, min_gap=0.20):

    if not events:
        return []

    events = sorted(
        float(x) for x in events
    )

    reduced = [events[0]]

    for event in events[1:]:

        if event - reduced[-1] >= min_gap:
            reduced.append(event)

    return reduced


# ============================================================
# EVENT DETECTION
# ============================================================

def detect_events(result):
    """
    Convert audio analysis into a unified event list.

    Every event has:

        {
            "time": float,
            "context": string
        }
    """

    events = []

    # --------------------------------------------------------
    # BEATS
    # --------------------------------------------------------

    for beat in result.get("beats", []):

        events.append({
            "time": float(beat),
            "context": "BEAT",
            "energy": 0.55
        })

    # --------------------------------------------------------
    # ONSETS
    # --------------------------------------------------------

    for onset in result.get("onsets", []):

        events.append({
            "time": float(onset),
            "context": "ONSET",
            "energy": 0.80
        })

    # --------------------------------------------------------
    # HIGH ENERGY
    # --------------------------------------------------------

    for event in result.get(
        "high_energy_events",
        []
    ):

        events.append({
            "time": float(event),
            "context": "HIGH_ENERGY",
            "energy": 0.95
        })

    # --------------------------------------------------------
    # LOW ENERGY
    # --------------------------------------------------------

    for event in result.get(
        "low_energy_events",
        []
    ):

        events.append({
            "time": float(event),
            "context": "LOW_ENERGY",
            "energy": 0.20
        })

    # --------------------------------------------------------
    # SORT BY TIME
    # --------------------------------------------------------

    events.sort(
        key=lambda x: x["time"]
    )

    return events


# ============================================================
# EVENT SUMMARY
# ============================================================

def show_event_summary(events):

    counts = {
        "LOW_ENERGY": 0,
        "BEAT": 0,
        "ONSET": 0,
        "HIGH_ENERGY": 0
    }

    for event in events:

        context = event["context"]

        if context in counts:
            counts[context] += 1

    print()
    print("==============================")
    print("       EVENT SUMMARY")
    print("==============================")

    print(
        f"LOW_ENERGY  : {counts['LOW_ENERGY']}"
    )

    print(
        f"BEAT        : {counts['BEAT']}"
    )

    print(
        f"ONSET       : {counts['ONSET']}"
    )

    print(
        f"HIGH_ENERGY : {counts['HIGH_ENERGY']}"
    )


# ============================================================
# VIRTUAL LIGHT SHOW
# ============================================================

def show_virtual_light_show(sequence, limit=30):

    print()
    print("==============================")
    print("     VIRTUAL LIGHT SHOW")
    print("==============================")

    for item in sequence[:limit]:

        action = item["action"]
        intensity = item["intensity"]

        bars = int(
            intensity * 20
        )

        empty = 20 - bars

        bar = (
            "█" * bars +
            "░" * empty
        )

        if action == "PULSE":
            icon = "💡"

        elif action == "FLASH":
            icon = "⚡"

        elif action == "STROBE":
            icon = "🔥"

        elif action == "DIM":
            icon = "🌑"

        else:
            icon = "💤"

        print(
            f"{icon} {action:<7} "
            f"[{bar}] "
            f"{intensity:.2f}"
        )


# ============================================================
# PRINT FIRST EVENTS
# ============================================================

def show_first_events(result):

    print()
    print("First 10 beat times:")

    for beat in result["beats"][:10]:
        print(
            f"{beat:.2f}s"
        )

    print()
    print("First 10 onset times:")

    for onset in result["onsets"][:10]:
        print(
            f"{onset:.2f}s"
        )


# ============================================================
# MAIN
# ============================================================

def main():

    print("Loading audio...")

    result = analyze_audio(
        AUDIO_PATH
    )

    # --------------------------------------------------------
    # MUSIC ANALYSIS
    # --------------------------------------------------------

    print()
    print("==============================")
    print("      MUSIC ANALYSIS")
    print("==============================")

    print(
        f"\nBPM: "
        f"{result['bpm']:.2f}"
    )

    print(
        f"Duration: "
        f"{result['duration']:.2f} seconds"
    )

    print(
        f"Average Energy: "
        f"{result['average_energy']:.4f}"
    )

    print(
        f"Spectral Centroid: "
        f"{result['spectral_centroid']:.2f}"
    )

    print()
    print(
        f"Detected Beats: "
        f"{len(result['beats'])}"
    )

    print(
        f"Detected Onsets: "
        f"{len(result['onsets'])}"
    )

    print(
        f"High Energy Events: "
        f"{len(result['high_energy_events'])}"
    )

    print(
        f"Low Energy Events: "
        f"{len(result['low_energy_events'])}"
    )

    show_first_events(
        result
    )

    # --------------------------------------------------------
    # EVENTS
    # --------------------------------------------------------

    events = detect_events(
        result
    )

    show_event_summary(
        events
    )

    # --------------------------------------------------------
    # LOAD DJ PROFILE
    # --------------------------------------------------------

    print()
    print("==============================")
    print("      LOADING DJ PROFILE")
    print("==============================")

    profile = DJProfile(
        "Test DJ"
    )

    if os.path.exists(
        PROFILE_PATH
    ):

        print(
            f"Profile file: "
            f"{os.path.basename(PROFILE_PATH)}"
        )

        profile.load(
            PROFILE_PATH
        )

    else:

        print(
            "Profile not found."
        )

    # --------------------------------------------------------
    # PROFILE
    # --------------------------------------------------------

    print()
    print("==============================")
    print("      LEARNED DJ PROFILE")
    print("==============================")

    profile.show_profile()

    # --------------------------------------------------------
    # GENERATE LIGHTING
    #
    # Uses the adaptive engine from
    # app.intelligence.lighting_decision (choose_adaptive_action
    # under the hood): energy-aware, repetition-aware, and
    # strobe-throttled.
    # --------------------------------------------------------

    sequence = generate_adaptive_lighting_sequence(
        events,
        profile
    )

    print()
    print("==============================")
    print("      LEARNED LIGHTING")
    print("==============================")

    for item in sequence[:30]:

        print(
            f"{item['time']:.2f}s → "
            f"{item['action']} | "
            f"Intensity: "
            f"{item['intensity']:.2f} | "
            f"Duration: "
            f"{item['duration']:.2f}s"
        )

    # --------------------------------------------------------
    # VIRTUAL SHOW
    # --------------------------------------------------------

    show_virtual_light_show(
        sequence
    )

    # --------------------------------------------------------
    # DECISION SUMMARY
    # --------------------------------------------------------

    print()
    print("==============================")
    print("    LEARNED DECISION SUMMARY")
    print("==============================")

    contexts = [
        "BEAT",
        "ONSET",
        "HIGH_ENERGY",
        "LOW_ENERGY"
    ]

    for context in contexts:

        action = choose_action(
            profile,
            context
        )

        print(
            f"{context:<12} → "
            f"{action}"
        )

    # --------------------------------------------------------
    # DONE
    # --------------------------------------------------------

    print()
    print("==============================")
    print("     SIMULATION COMPLETE")
    print("==============================")


# ============================================================
# IMPORTANT:
# Only run main() when analyzer.py itself is executed.
# When live_feedback imports analyze_audio(), it will NOT
# automatically run the whole analyzer.
# ============================================================

if __name__ == "__main__":

    # Windows consoles often default to a non-UTF-8 codepage
    # (e.g. cp1252), which crashes on the emoji/arrow characters
    # used in this file's console output. Reconfigure stdout to
    # UTF-8 (falling back to safe substitution) before printing.
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    main()