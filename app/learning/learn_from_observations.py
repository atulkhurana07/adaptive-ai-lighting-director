from app.learning.dj_profile import DJProfile
from app.observation.dj_observer import DJObserver


def learn_from_observations(
    observer,
    profile
):
    """
    Learn the DJ's preferred lighting actions
    from recorded observations.
    """

    for observation in observer.get_observations():

        ai_action = observation["ai_action"]
        dj_action = observation["dj_action"]
        feedback = observation["feedback"]
        context = observation["music_event"]

        if feedback > 0:

            # DJ accepted the AI's action (ai_action == dj_action
            # for an accepted observation) -- reward it once.
            # Rewarding dj_action too would double-count the same
            # action.
            profile.observe(
                ai_action,
                rating=feedback,
                context=context
            )

        elif feedback < 0:

            # DJ rejected the AI's action: penalize what the AI
            # chose, and reward what the DJ chose instead.
            profile.observe(
                ai_action,
                rating=feedback,
                context=context
            )

            profile.observe(
                dj_action,
                rating=abs(feedback),
                context=context
            )


if __name__ == "__main__":

    observer = DJObserver("Test DJ")

    observer.load(
        "data/dj_observations/test_dj.json"
    )

    profile = DJProfile("Test DJ")

    profile.load(
        "data/dj_profiles/test_dj.json"
    )

    print("\n==============================")
    print("      BEFORE LEARNING")
    print("==============================")

    profile.show_profile()

    # Learn from DJ observations
    learn_from_observations(
        observer,
        profile
    )

    print("\n==============================")
    print("       AFTER LEARNING")
    print("==============================")

    profile.show_profile()

    # Save updated profile
    profile.save(
        "data/dj_profiles/test_dj.json"
    )

    print("\nDJ profile updated!")