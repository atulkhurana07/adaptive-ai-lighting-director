from app.learning.dj_profile import DJProfile


def record_dj_feedback(
    dj_profile,
    event,
    ai_action,
    dj_action
):
    """
    Learn from the DJ's actual lighting choice.

    If DJ accepts the AI action:
        AI action gets positive feedback.

    If DJ changes the action:
        DJ's chosen action gets positive feedback.
        AI's original action gets negative feedback.
    """

    context = event["type"]

    # --------------------------------
    # DJ ACCEPTED AI DECISION
    # --------------------------------

    if ai_action == dj_action:

        dj_profile.observe(
            lighting_action=dj_action,
            rating=1.0,
            context=context
        )

        return {
            "context": context,
            "ai_action": ai_action,
            "dj_action": dj_action,
            "result": "ACCEPTED"
        }

    # --------------------------------
    # DJ CHANGED AI DECISION
    # --------------------------------

    else:

        # Reward what the DJ actually chose
        dj_profile.observe(
            lighting_action=dj_action,
            rating=1.0,
            context=context
        )

        # Penalize what the AI originally chose
        dj_profile.observe(
            lighting_action=ai_action,
            rating=-1.0,
            context=context
        )

        return {
            "context": context,
            "ai_action": ai_action,
            "dj_action": dj_action,
            "result": "CHANGED"
        }