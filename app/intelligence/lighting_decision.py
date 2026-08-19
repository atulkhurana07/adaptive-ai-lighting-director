# app/intelligence/lighting_decision.py

"""
Adaptive AI Lighting Decision Engine

Uses:
- Learned DJ preferences
- Music context
- Energy level
- Previous lighting action
- Event timing
- Repetition control

The output is deterministic so the same input produces
the same lighting decisions.
"""

ACTIONS = [
    "PULSE",
    "FLASH",
    "STROBE",
    "DIM",
    "IDLE"
]

# Actions considered by the adaptive engine (choose_adaptive_action /
# generate_lighting_sequence). IDLE is intentionally excluded: it is
# never a meaningful response to a detected music event, and unlike
# choose_action() (which has a "best_score > 0" guard) the adaptive
# engine's plain max() would otherwise let IDLE win by default
# whenever every real action scores negative.
ADAPTIVE_ACTIONS = [
    "PULSE",
    "FLASH",
    "STROBE",
    "DIM"
]

# Weight applied to the normalized ([-1, 1]) learned preference inside
# _context_score(). Bounded so a maxed-out learned preference (+/-1)
# contributes at most +/-LEARNED_WEIGHT -- comparable to a single
# context bonus and strictly less than the strobe-throttle penalty,
# so learning can influence but not overwhelm context/energy/
# repetition/strobe-spacing.
LEARNED_WEIGHT = 4.0


# ============================================================
# BASIC LEARNED DECISION
# ============================================================

def choose_action(profile, context):
    """
    Choose the strongest learned action for a context.

    Context preference has priority over overall preference.
    """

    context = str(context).upper()

    context_preferences = getattr(
        profile,
        "context_preferences",
        {}
    )

    preferences = context_preferences.get(
        context,
        {}
    )

    # --------------------------------------------------------
    # Use context-specific learning
    # --------------------------------------------------------

    if preferences:

        scores = {
            action: float(
                preferences.get(action, 0.0)
            )
            for action in ACTIONS
        }

        best_score = max(scores.values())

        if best_score > 0:

            best_actions = [
                action
                for action in ACTIONS
                if scores[action] == best_score
            ]

            # Deterministic tie-breaking
            return best_actions[0]

    # --------------------------------------------------------
    # Use overall learning
    # --------------------------------------------------------

    overall = getattr(
        profile,
        "preferences",
        {}
    )

    if overall:

        scores = {
            action: float(
                overall.get(action, 0.0)
            )
            for action in ACTIONS
        }

        best_score = max(scores.values())

        if best_score > 0:

            best_actions = [
                action
                for action in ACTIONS
                if scores[action] == best_score
            ]

            return best_actions[0]

    # --------------------------------------------------------
    # Default
    # --------------------------------------------------------

    return "PULSE"


# ============================================================
# CONFIDENCE
# ============================================================

def get_confidence(profile, context):
    """
    Calculate confidence from positive learned scores.
    """

    context = str(context).upper()

    context_preferences = getattr(
        profile,
        "context_preferences",
        {}
    )

    preferences = context_preferences.get(
        context,
        {}
    )

    if not preferences:
        return 0.0

    positive_scores = [
        max(
            0.0,
            float(
                preferences.get(action, 0.0)
            )
        )
        for action in ACTIONS
    ]

    total = sum(positive_scores)

    if total <= 0:
        return 0.0

    best = max(positive_scores)

    return min(
        best / total,
        1.0
    )


# ============================================================
# CONTEXT + ENERGY SCORE
# ============================================================

def _context_score(
    profile,
    action,
    context,
    energy
):
    """
    Convert learned preferences into a usable decision score.

    Context and energy are combined into a single term rather than
    two separately-added blocks: energy is currently derived purely
    from context (see _get_event_energy), so scoring them as two
    independent additive bonuses double-counts the same underlying
    signal for HIGH_ENERGY/ONSET/LOW_ENERGY events. Here, energy
    instead scales the context bonus once, via energy_multiplier.
    """

    learned = profile.get_normalized_context_preference(
        context,
        action
    )

    score = learned * LEARNED_WEIGHT

    energy_multiplier = 0.5 + energy

    # --------------------------------------------------------
    # Music-context behavior
    # --------------------------------------------------------

    context_bonus = 0.0

    if context == "HIGH_ENERGY":

        if action == "STROBE":
            context_bonus = 5.0

        elif action == "FLASH":
            context_bonus = 3.0

        elif action == "PULSE":
            context_bonus = 1.0

        elif action == "DIM":
            context_bonus = -5.0

    elif context == "ONSET":

        if action == "FLASH":
            context_bonus = 4.0

        elif action == "STROBE":
            context_bonus = 2.0

        elif action == "PULSE":
            context_bonus = 1.0

        elif action == "DIM":
            context_bonus = -3.0

    elif context == "BEAT":

        if action == "FLASH":
            context_bonus = 3.0

        elif action == "PULSE":
            context_bonus = 2.0

        elif action == "STROBE":
            context_bonus = 1.0

    elif context == "LOW_ENERGY":

        if action == "PULSE":
            context_bonus = 4.0

        elif action == "DIM":
            context_bonus = 3.0

        elif action == "FLASH":
            context_bonus = 1.0

        elif action == "STROBE":
            context_bonus = -5.0

    score += context_bonus * energy_multiplier

    return score


# ============================================================
# ADAPTIVE ACTION
# ============================================================

def choose_adaptive_action(
    profile,
    context,
    previous_action=None,
    energy=0.5,
    last_strobe_time=None,
    current_time=None
):
    """
    Intelligent deterministic lighting decision.

    Considers:
    - learned DJ preferences
    - context
    - energy
    - repetition
    - STROBE-specific cooldown spacing

    IDLE is excluded from selection -- see ADAPTIVE_ACTIONS.

    last_strobe_time is the timestamp STROBE was last actually
    selected (not the timestamp of the previous event of any kind)
    -- see the "Don't strobe too frequently" block below.
    """

    context = str(context).upper()

    scores = {}

    # --------------------------------------------------------
    # Calculate scores
    # --------------------------------------------------------

    for action in ADAPTIVE_ACTIONS:

        score = _context_score(
            profile,
            action,
            context,
            energy
        )

        # ----------------------------------------------------
        # Repetition control
        # ----------------------------------------------------

        if previous_action == action:

            if action == "FLASH":
                score -= 4.0

            elif action == "PULSE":
                score -= 1.5

            elif action == "STROBE":
                score -= 3.0

            elif action == "DIM":
                score -= 1.0

        # ----------------------------------------------------
        # Don't strobe too frequently
        #
        # Cooldown is measured against the last time STROBE was
        # actually selected, not the last event of any kind --
        # events occur every ~0.1-0.2s, so using "any previous
        # event" would penalize STROBE almost constantly and it
        # would never win, regardless of context/energy/learning.
        # ----------------------------------------------------

        if action == "STROBE":

            if (
                last_strobe_time is not None
                and current_time is not None
            ):

                gap = (
                    float(current_time)
                    - float(last_strobe_time)
                )

                if gap < 0.50:
                    score -= 8.0

        scores[action] = score

    # --------------------------------------------------------
    # Find best action
    # --------------------------------------------------------

    best_action = max(
        scores,
        key=scores.get
    )

    return best_action


# ============================================================
# INTENSITY
# ============================================================

def calculate_intensity(
    action,
    context,
    energy
):
    """
    Calculate lighting intensity.
    """

    action = str(action).upper()
    context = str(context).upper()

    energy = max(
        0.0,
        min(
            1.0,
            float(energy)
        )
    )

    # --------------------------------------------------------
    # STROBE
    # --------------------------------------------------------

    if action == "STROBE":

        if context == "HIGH_ENERGY":
            intensity = 0.85 + (
                energy * 0.15
            )

        else:
            intensity = 0.70 + (
                energy * 0.20
            )

    # --------------------------------------------------------
    # FLASH
    # --------------------------------------------------------

    elif action == "FLASH":

        if context == "ONSET":
            intensity = 0.65 + (
                energy * 0.25
            )

        elif context == "BEAT":
            intensity = 0.50 + (
                energy * 0.20
            )

        else:
            intensity = 0.40 + (
                energy * 0.20
            )

    # --------------------------------------------------------
    # PULSE
    # --------------------------------------------------------

    elif action == "PULSE":

        intensity = 0.25 + (
            energy * 0.30
        )

    # --------------------------------------------------------
    # DIM
    # --------------------------------------------------------

    elif action == "DIM":

        intensity = 0.10 + (
            energy * 0.15
        )

    # --------------------------------------------------------
    # IDLE
    # --------------------------------------------------------

    else:

        intensity = 0.0

    return round(
        min(
            1.0,
            max(
                0.0,
                intensity
            )
        ),
        2
    )


# ============================================================
# DURATION
# ============================================================

def calculate_duration(
    action,
    context
):
    """
    Calculate effect duration.
    """

    action = str(action).upper()
    context = str(context).upper()

    if action == "STROBE":
        return 0.12

    if action == "FLASH":
        return 0.15

    if action == "PULSE":
        return 0.25

    if action == "DIM":
        return 0.35

    return 0.20


# ============================================================
# EVENT ENERGY
# ============================================================

def _get_event_energy(event):
    """
    Estimate energy from event context.
    """

    context = str(
        event.get(
            "context",
            event.get(
                "type",
                "IDLE"
            )
        )
    ).upper()

    if context == "HIGH_ENERGY":
        return 0.95

    if context == "ONSET":
        return 0.80

    if context == "BEAT":
        return 0.55

    if context == "LOW_ENERGY":
        return 0.20

    return 0.50


# ============================================================
# GENERATE LIGHTING SEQUENCE
# ============================================================

def generate_lighting_sequence(
    events,
    profile
):
    """
    Generate an intelligent lighting timeline.

    Improvements:
    - Removes duplicate events at almost identical times
    - Reduces excessive FLASH repetition
    - Uses learned DJ profile
    - Uses energy
    - Controls STROBE frequency
    - Produces deterministic output
    """

    if not events:
        return []

    # --------------------------------------------------------
    # Sort events
    # --------------------------------------------------------

    sorted_events = sorted(
        events,
        key=lambda event: float(
            event.get(
                "time",
                event.get(
                    "timestamp",
                    event.get(
                        "start",
                        0.0
                    )
                )
            )
        )
    )

    # --------------------------------------------------------
    # Remove duplicate/near-duplicate events
    #
    # If two events happen within 0.08 sec,
    # keep the stronger context.
    # --------------------------------------------------------

    priority = {
        "HIGH_ENERGY": 4,
        "ONSET": 3,
        "BEAT": 2,
        "LOW_ENERGY": 1,
        "IDLE": 0
    }

    filtered_events = []

    for event in sorted_events:

        time = float(
            event.get(
                "time",
                event.get(
                    "timestamp",
                    event.get(
                        "start",
                        0.0
                    )
                )
            )
        )

        context = str(
            event.get(
                "context",
                event.get(
                    "type",
                    "IDLE"
                )
            )
        ).upper()

        current = {
            "time": time,
            "context": context
        }

        if not filtered_events:

            filtered_events.append(
                current
            )
            continue

        previous = filtered_events[-1]

        gap = (
            time
            - previous["time"]
        )

        if gap < 0.08:

            if priority.get(
                context,
                0
            ) > priority.get(
                previous["context"],
                0
            ):

                filtered_events[-1] = current

        else:

            filtered_events.append(
                current
            )

    # --------------------------------------------------------
    # Generate sequence
    # --------------------------------------------------------

    sequence = []

    # Local to this call -- reset every time generate_lighting_sequence()
    # runs, not persisted across calls (nothing in the architecture
    # requires cooldown state to survive between separate sequences).
    previous_action = None
    last_strobe_time = None

    for event in filtered_events:

        time = event["time"]
        context = event["context"]

        energy = _get_event_energy(
            event
        )

        action = choose_adaptive_action(
            profile=profile,
            context=context,
            previous_action=previous_action,
            energy=energy,
            last_strobe_time=last_strobe_time,
            current_time=time
        )

        intensity = calculate_intensity(
            action,
            context,
            energy
        )

        duration = calculate_duration(
            action,
            context
        )

        sequence.append({
            "time": round(
                time,
                2
            ),
            "action": action,
            "intensity": intensity,
            "duration": duration,
            "context": context
        })

        previous_action = action

        # Only an actual STROBE selection resets the cooldown clock --
        # FLASH/PULSE/DIM selections must not affect it.
        if action == "STROBE":
            last_strobe_time = time

    return sequence