from app.observation.dj_observer import DJObserver


# Manual demo script, not an automated test -- writes to a dedicated
# demo observations file, never the real data/dj_observations/test_dj.json
# used by the actual product/DJ.
OBSERVATIONS_PATH = "data/dj_observations/demo_dj.json"


observer = DJObserver("Test DJ")


# Simulate the DJ making different choices
observer.record_observation(
    time=2.14,
    music_event="BEAT",
    ai_action="PULSE",
    dj_action="FLASH",
    feedback=1.0
)

observer.record_observation(
    time=5.13,
    music_event="HIGH_ENERGY",
    ai_action="STROBE",
    dj_action="STROBE",
    feedback=1.0
)

observer.record_observation(
    time=8.42,
    music_event="LOW_ENERGY",
    ai_action="DIM",
    dj_action="PULSE",
    feedback=-1.0
)


observer.show_observations()


# Save observations
observer.save(
    OBSERVATIONS_PATH
)

print("\nObservations saved!")