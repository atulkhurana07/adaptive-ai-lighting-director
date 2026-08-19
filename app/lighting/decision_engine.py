def create_lighting_decision(event, dj_profile):
    """
    Combine musical context with the DJ's
    learned context-specific preferences.
    """

    event_type = event["type"]
    base_intensity = event["intensity"]

    # Default lighting action based on music
    default_actions = {
        "BEAT": "PULSE",
        "ONSET": "FLASH",
        "HIGH_ENERGY": "STROBE",
        "LOW_ENERGY": "DIM"
    }

    default_action = default_actions.get(
        event_type,
        "PULSE"
    )

    # Available lighting actions
    scores = {
        "PULSE": 0.0,
        "FLASH": 0.0,
        "STROBE": 0.0,
        "DIM": 0.0
    }

    # --------------------------------
    # 1. MUSIC CONTEXT
    # --------------------------------

    scores[default_action] += 2.0

    # --------------------------------
    # 2. DJ CONTEXT-SPECIFIC LEARNING
    # --------------------------------

    for action in scores:

        context_preference = (
            dj_profile.get_context_preference(
                event_type,
                action
            )
        )

        scores[action] += (
            context_preference * 2.0
        )

    # --------------------------------
    # 3. OVERALL DJ PREFERENCE
    # --------------------------------

    for action in scores:

        overall_preference = (
            dj_profile.get_preference(action)
        )

        scores[action] += (
            overall_preference * 0.2
        )

    # --------------------------------
    # 4. SELECT BEST ACTION
    # --------------------------------

    selected_action = max(
        scores,
        key=scores.get
    )

    return {
        "action": selected_action,
        "intensity": base_intensity,
        "duration": 0.20
    }