import sys

from app.learning.dj_profile import DJProfile


# Manual demo script, not an automated test -- writes to a dedicated
# demo profile file, never the real data/dj_profiles/test_dj.json used
# by the actual product/DJ.
PROFILE_PATH = "data/dj_profiles/demo_dj.json"


def main():

    # Create a new DJ
    dj = DJProfile("Test DJ")

    print("\nBEFORE LEARNING")
    dj.show_profile()

    # Simulate the DJ's choices
    # Imagine the DJ repeatedly chooses STROBE
    print("\nLearning from DJ...")

    dj.observe("STROBE", rating=1.0)
    dj.observe("STROBE", rating=1.0)
    dj.observe("STROBE", rating=1.0)

    # DJ also likes PULSE sometimes
    dj.observe("PULSE", rating=0.5)

    print("\nAFTER LEARNING")
    dj.show_profile()

    # Save the learned profile
    dj.save(PROFILE_PATH)

    print("\nDJ profile saved!")


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
