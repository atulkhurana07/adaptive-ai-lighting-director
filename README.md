# Adaptive AI Lighting Director

An AI that listens to a track, directs the stage lighting in real time, watches how a DJ reacts, and adjusts its future decisions to that DJ's personal taste.

## Why this isn't a music visualizer

A traditional visualizer maps audio features (beat, volume) directly to a fixed visual rule: "loud → flash," every time, for every user, forever. This project instead runs those audio features through a **learned decision engine**. The engine starts with sensible defaults, but every time a DJ accepts or overrides a lighting choice, that feedback is recorded and folded back into the engine's per-DJ, per-musical-context preferences. The next time a similar moment occurs, the engine's decision reflects what *that specific DJ* has taught it — not a fixed rule table.

## How it works — the loop

```
Music (MP3)
   │
   ▼
Audio Analysis        librosa: BPM, beat times, onsets, RMS energy, spectral centroid
   │
   ▼
Event Detection        beats / onsets / high-energy / low-energy moments, timestamped
   │
   ▼
Adaptive Decision       learned DJ preference + musical context + energy + repetition
   │                    control + STROBE cooldown  →  PULSE / FLASH / STROBE / DIM
   ▼
Virtual Lighting        the chosen action, intensity, and duration for that moment
   │
   ▼
DJ Feedback             DJ keeps the AI's choice, or picks a different action
   │
   ▼
Learning                the DJ's response updates a per-context preference score
   │
   └──────────────────► feeds back into Adaptive Decision for future moments
```

## The AI learning loop, concretely

- Every lighting decision is scored per action (`PULSE`, `FLASH`, `STROBE`, `DIM`) from a blend of: the DJ's **learned preference** for that action in that musical context (normalized with `tanh` so it saturates rather than growing unbounded), a **musical-context bonus** (e.g. STROBE suits a high-energy moment more than a quiet one), an **energy multiplier**, a **repetition penalty** (discourages picking the same action twice in a row), and a **STROBE-specific cooldown** (STROBE can't fire again within 0.5s of the last real STROBE, regardless of what happened in between).
- The learned-preference term is deliberately weighted so it can *influence* the decision but never *override* the musical context or the safety cooldowns — a DJ who loves STROBE can still not get two STROBEs 0.1s apart.
- `IDLE` is intentionally excluded from adaptive decisions — the engine always produces an active lighting choice for a detected musical moment.
- Feedback is stored both as a per-DJ preference profile (`DJProfile`) and as a raw observation log (`DJObserver`), so the "why" behind every learned adjustment is auditable.

## Tech stack

- **Python 3.12**
- **librosa** — audio analysis (BPM, beat/onset detection, RMS energy, spectral centroid)
- **NumPy** — numerical support for librosa
- **Streamlit** — the demo dashboard UI

No other dependencies. The decision/learning engine itself has zero third-party dependencies — it's plain Python.

## Project structure

```
app/
  audio/          analyze_audio(), detect_events() -- turns an MP3 into timestamped musical moments
  intelligence/    lighting_decision.py -- the ONE adaptive decision engine (generate_lighting_sequence(),
                   choose_adaptive_action(), STROBE cooldown, normalization constants)
  learning/        dj_profile.py -- DJProfile (learned preferences, save/load)
                   feedback.py, live_feedback.py, interactive_feedback.py, learn_from_observations.py --
                   CLI entry points that exercise the learning loop
  observation/     dj_observer.py -- DJObserver, the raw feedback-event log
  lighting/        decision_engine.py -- an older, simpler scoring function retained for one legacy
                   CLI script (see Known limitations)
  ui/              streamlit_app.py -- the demo dashboard; a presentation layer only, calls the
                   functions above directly and never re-implements any scoring/learning logic
data/
  raw/             sample track used by the demo (test_song.mp3)
  dj_profiles/     saved DJ preference profiles (JSON)
  dj_observations/ saved raw feedback logs (JSON)
```

## How to run

```bash
pip install -r requirements.txt
streamlit run app/ui/streamlit_app.py
```

This opens the dashboard in your browser. Use **Try Demo Track** in the sidebar for the fastest path to a working demo, or upload your own MP3.

CLI entry points also exist for the underlying pipeline, useful for inspecting raw output without the UI:

```bash
python -m app.audio.analyzer          # full pipeline, prints analysis + generated lighting sequence
python -m app.learning.live_feedback  # same, plus an interactive terminal feedback loop
```

## Demo instructions

1. Launch the app (`streamlit run app/ui/streamlit_app.py`).
2. Click **Try Demo Track** in the sidebar (or upload your own MP3).
3. Watch the **AI Director** panel — it shows the currently chosen lighting action, live, driven by the actual audio analysis.
4. Use **Keep it** to confirm a decision, or **Change it** to tell the AI what you'd have chosen instead.
5. Watch the **AI Learning** panel update — the bar for the action you picked moves, and the moment is logged under **Recent Learning**.
6. Step through more moments (**Next ›**) and notice that the AI's choices in similar contexts start reflecting what you just taught it.
7. Toggle **Developer view** to see the raw learned scores, the full generated sequence, and the raw observation log behind the demo.

All interactive feedback in the UI is saved to a private demo profile (`data/dj_profiles/demo_dj.json`, `data/dj_observations/demo_dj.json`) — it never touches the shipped sample profile (`test_dj.json`). Use **Reset AI Learning** in the sidebar to start the demo profile over.

## Example workflow (what actually happens under the hood)

```python
result   = analyze_audio("data/raw/test_song.mp3")   # BPM, beats, onsets, energy...
events   = detect_events(result)                      # [{time, context, energy}, ...]
sequence = generate_lighting_sequence(events, profile) # [{time, action, intensity, duration, context}, ...]

# DJ reviews sequence[i], accepts or overrides sequence[i]["action"]:
profile.observe(dj_chosen_action, rating=1.0, context=sequence[i]["context"])

# Next call to generate_lighting_sequence() with the same profile reflects that feedback.
```

## Known limitations

- The dashboard's "AI Director" panel intentionally does not display a numeric confidence percentage. An earlier version paired the adaptive engine's chosen action with a confidence value computed by a *different*, simpler decision function — the two could occasionally disagree, which would have shown a confidence number for the wrong action. Rather than invent a new metric, the UI now shows an honest, action-independent read on whether that musical context has been taught at all ("Choosing based on this moment" vs. "Learned from your feedback"). The original confidence value is still visible, correctly labeled, in Developer view.
- `app/lighting/decision_engine.py` contains an older, simpler scoring function used only by the legacy `app/learning/interactive_feedback.py` CLI demo script. It is not part of the main adaptive pipeline and is kept rather than deleted since it still has a working caller.
- A handful of standalone demo/test scripts (`app/learning/learning_test.py`, `test_learning.py`, `test_feedback.py`, `app/observation/observer_test.py`) exist for manual backend exploration; they write to the same demo data path as the UI and are not part of the product surface.
