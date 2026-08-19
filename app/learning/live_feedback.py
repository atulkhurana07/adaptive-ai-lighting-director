from app.audio.analyzer import analyze_audio, detect_events
from app.learning.dj_profile import DJProfile
from app.observation.dj_observer import DJObserver
from app.intelligence.lighting_decision import (
    choose_action,
    get_confidence,
    generate_lighting_sequence as generate_adaptive_lighting_sequence,
)

import os
import sys


PROFILE_PATH = "data/dj_profiles/test_dj.json"
OBSERVATIONS_PATH = "data/dj_observations/test_dj.json"
AUDIO_PATH = "data/raw/test_song.mp3"


ACTIONS = {
    1: "PULSE",
    2: "FLASH",
    3: "STROBE",
    4: "DIM"
}


def get_context(event):
    return event.get(
        "context",
        event.get("type", "IDLE")
    )


def get_time(event):
    return event.get(
        "time",
        event.get(
            "timestamp",
            event.get("start", 0.0)
        )
    )


def main():

    print()
    print("==============================")
    print("     LIVE DJ LEARNING")
    print("==============================")

    # -----------------------------
    # LOAD PROFILE
    # -----------------------------

    profile = DJProfile("Test DJ")

    if os.path.exists(PROFILE_PATH):
        profile.load(PROFILE_PATH)

    print(
        f"Current observations: "
        f"{profile.observations}"
    )

    # -----------------------------
    # LOAD OBSERVATION LOG
    #
    # Loading existing records before recording new ones means
    # save() below writes them back untouched alongside anything
    # new from this session.
    # -----------------------------

    observer = DJObserver("Test DJ")

    if os.path.exists(OBSERVATIONS_PATH):
        observer.load(OBSERVATIONS_PATH)

    # -----------------------------
    # ANALYZE MUSIC
    # -----------------------------

    print()
    print("Loading audio...")

    result = analyze_audio(
        AUDIO_PATH
    )

    # -----------------------------
    # GET EVENTS
    #
    # Uses the canonical event detector from app.audio.analyzer
    # (same {time, context, energy} schema) instead of duplicating
    # the event-building logic here.
    # -----------------------------

    events = detect_events(result)

    print()
    print(
        f"Total events detected: "
        f"{len(events)}"
    )

    # -----------------------------
    # ADAPTIVE LIGHTING SEQUENCE
    #
    # Run the SAME adaptive engine the real lighting pipeline uses
    # (app.audio.analyzer.main() calls this identical function) so
    # the AI suggestion shown to the DJ below is the actual decision
    # the lighting system evaluated for that event -- including its
    # repetition/energy/STROBE-cooldown state -- not a separate,
    # simpler re-decision.
    # -----------------------------

    sequence = generate_adaptive_lighting_sequence(
        events,
        profile
    )

    # -----------------------------
    # SELECT FEEDBACK EVENTS
    # -----------------------------

    # Don't ask the DJ hundreds of questions.
    # Select a few representative events from the sequence the AI
    # actually produced above (post-dedup), one per unique context.

    selected_events = []

    contexts_used = set()

    for item in sequence:

        context = item["context"]

        if context not in contexts_used:

            selected_events.append(item)
            contexts_used.add(context)

    # Maximum 4 feedback questions.
    selected_events = selected_events[:4]

    print(
        f"Events selected for DJ feedback: "
        f"{len(selected_events)}"
    )

    # -----------------------------
    # INTERACTIVE LEARNING
    # -----------------------------

    for event in selected_events:

        context = event["context"]
        time = event["time"]

        # The action the adaptive engine actually assigned to this
        # event in the real lighting sequence above -- not a
        # separate re-decision via choose_action().
        ai_action = event["action"]

        confidence = get_confidence(
            profile,
            context
        )

        print()
        print("------------------------------")

        print(
            f"Music time: "
            f"{time:.2f}s"
        )

        print(
            f"Music context: "
            f"{context}"
        )

        print(
            f"AI chose: "
            f"{ai_action}"
        )

        print(
            f"AI confidence: "
            f"{confidence * 100:.1f}%"
        )

        print()
        print("What did the DJ choose?")
        print("1. PULSE")
        print("2. FLASH")
        print("3. STROBE")
        print("4. DIM")
        print("5. Skip")

        while True:

            choice = input(
                "\nChoice: "
            ).strip()

            if choice == "5":

                print(
                    "Skipped."
                )

                break

            if choice in ["1", "2", "3", "4"]:

                dj_action = ACTIONS[
                    int(choice)
                ]

                if dj_action == ai_action:

                    print()
                    print(
                        f"DJ chose: "
                        f"{dj_action}"
                    )

                    print(
                        "Result: ACCEPTED"
                    )

                    # Positive feedback
                    profile.observe(
                        dj_action,
                        rating=1.0,
                        context=context
                    )

                else:

                    print()
                    print(
                        f"DJ chose: "
                        f"{dj_action}"
                    )

                    print(
                        "Result: CHANGED"
                    )

                    # Penalize AI's wrong decision
                    profile.observe(
                        ai_action,
                        rating=-1.0,
                        context=context
                    )

                    # Reward DJ's actual choice
                    profile.observe(
                        dj_action,
                        rating=1.0,
                        context=context
                    )

                # Save immediately
                profile.save(
                    PROFILE_PATH
                )

                # Record this real feedback event (Skip never
                # reaches this point, so Skip never creates an
                # observation). Uses the same time/context/
                # ai_action/dj_action already computed above --
                # no re-detection or re-decision.
                observer.record_observation(
                    time=time,
                    music_event=context,
                    ai_action=ai_action,
                    dj_action=dj_action,
                    feedback=1.0 if dj_action == ai_action else -1.0
                )

                # Save immediately so a session isn't lost
                # if interrupted.
                observer.save(
                    OBSERVATIONS_PATH
                )

                # Show what AI would choose now
                new_action = choose_action(
                    profile,
                    context
                )

                print()
                print(
                    f"Updated AI decision: "
                    f"{new_action}"
                )

                break

            print(
                "Invalid choice. "
                "Enter 1-5."
            )

    # -----------------------------
    # FINAL RESULT
    # -----------------------------

    print()
    print("==============================")
    print("     LEARNING COMPLETE")
    print("==============================")

    profile.show_profile()

    print()
    print("==============================")
    print("   UPDATED AI DECISIONS")
    print("==============================")

    for context in [
        "BEAT",
        "ONSET",
        "HIGH_ENERGY",
        "LOW_ENERGY"
    ]:

        action = choose_action(
            profile,
            context
        )

        confidence = get_confidence(
            profile,
            context
        )

        print(
            f"{context:<12} → "
            f"{action:<7} "
            f"({confidence * 100:.1f}%)"
        )


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