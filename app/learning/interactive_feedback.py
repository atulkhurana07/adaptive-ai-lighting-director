"""
Manual, standalone demo of the DJ feedback loop.

Uses the same adaptive lighting engine
(app.intelligence.lighting_decision.generate_lighting_sequence) as the
real product pipeline (app.audio.analyzer.main(), app.learning.
live_feedback.main()) -- there is only one authoritative adaptive
decision path project-wide, this script does not run a separate one.

Writes to a dedicated demo profile file, never the real
data/dj_profiles/test_dj.json used by the actual product/DJ.
"""

from app.learning.dj_profile import DJProfile
from app.learning.feedback import record_dj_feedback
from app.intelligence.lighting_decision import generate_lighting_sequence


PROFILE_PATH = "data/dj_profiles/demo_dj.json"

ACTIONS = [
    "PULSE",
    "FLASH",
    "STROBE",
    "DIM"
]


def get_dj_choice():

    print("\nWhat did the DJ choose?")

    for i, action in enumerate(ACTIONS, start=1):
        print(f"{i}. {action}")

    print("5. Skip")

    while True:

        choice = input("\nChoice: ").strip()

        if choice in ["1", "2", "3", "4"]:
            return ACTIONS[int(choice) - 1]

        if choice == "5":
            return None

        print("Invalid choice. Enter 1-5.")


def main():

    dj = DJProfile("Test DJ")

    dj.load(
        PROFILE_PATH
    )

    print("\n==============================")
    print("   INTERACTIVE DJ FEEDBACK")
    print("==============================")

    print(
        f"\nCurrent observations: "
        f"{dj.observations}"
    )

    # Test events -- adaptive-engine schema (time/context), not the
    # old type/intensity schema create_lighting_decision() used.
    test_events = [
        {
            "time": 0.0,
            "context": "BEAT"
        },
        {
            "time": 1.0,
            "context": "HIGH_ENERGY"
        },
        {
            "time": 2.0,
            "context": "LOW_ENERGY"
        }
    ]

    # Run the SAME adaptive engine the real pipeline uses, once, over
    # all test events -- this correctly threads repetition/STROBE-
    # cooldown state across them, exactly like the real product does.
    # No separate scoring logic is implemented here.
    sequence = generate_lighting_sequence(
        test_events,
        dj
    )

    for item in sequence:

        context = item["context"]
        ai_action = item["action"]

        print("\n------------------------------")

        print(
            f"Music Context: "
            f"{context}"
        )

        print(
            f"AI chose: "
            f"{ai_action}"
        )

        dj_action = get_dj_choice()

        if dj_action is None:
            print("Skipped.")
            continue

        result = record_dj_feedback(
            dj,
            {"type": context},
            ai_action,
            dj_action
        )

        print(
            f"\nDJ chose: {dj_action}"
        )

        print(
            f"Result: {result['result']}"
        )

    # Save learned profile
    dj.save(
        PROFILE_PATH
    )

    print("\n==============================")
    print("     LEARNING COMPLETE")
    print("==============================")

    dj.show_profile()


if __name__ == "__main__":
    main()