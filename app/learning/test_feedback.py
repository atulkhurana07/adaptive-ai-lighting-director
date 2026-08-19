import sys

from app.learning.dj_profile import DJProfile
from app.learning.feedback import record_dj_feedback


# Manual demo script, not an automated test -- writes to a dedicated
# demo profile file, never the real data/dj_profiles/test_dj.json used
# by the actual product/DJ.
PROFILE_PATH = "data/dj_profiles/demo_dj.json"


def main():

    dj = DJProfile("Test DJ")

    dj.load(PROFILE_PATH)

    print("\n==============================")
    print("     BEFORE FEEDBACK")
    print("==============================")

    dj.show_profile()

    # --------------------------------
    # SIMULATE DJ FEEDBACK
    # --------------------------------

    event = {
        "type": "BEAT",
        "intensity": 0.5
    }

    ai_action = "PULSE"

    dj_action = "FLASH"

    result = record_dj_feedback(
        dj,
        event,
        ai_action,
        dj_action
    )

    print("\n==============================")
    print("     FEEDBACK")
    print("==============================")

    print(
        f"Context: {result['context']}"
    )

    print(
        f"AI Action: {result['ai_action']}"
    )

    print(
        f"DJ Action: {result['dj_action']}"
    )

    print(
        f"Result: {result['result']}"
    )

    # --------------------------------
    # SAVE LEARNING
    # --------------------------------

    dj.save(
        PROFILE_PATH
    )

    print("\n==============================")
    print("      AFTER LEARNING")
    print("==============================")

    dj.show_profile()


if __name__ == "__main__":

    # Windows consoles often default to a non-UTF-8 codepage
    # (e.g. cp1252), which crashes on the emoji/arrow characters
    # used in DJProfile.show_profile()'s output. Reconfigure stdout
    # to UTF-8 (falling back to safe substitution) before printing --
    # same approach as app/audio/analyzer.py and
    # app/learning/live_feedback.py.
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    main()
