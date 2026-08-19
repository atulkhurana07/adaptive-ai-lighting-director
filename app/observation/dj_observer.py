import json
import os
from datetime import datetime


class DJObserver:

    def __init__(self, dj_name="Test DJ"):
        self.dj_name = dj_name
        self.observations = []

    def record_observation(
        self,
        time,
        music_event,
        ai_action,
        dj_action,
        feedback=0.0
    ):
        """
        Record what the AI suggested and what
        the DJ actually did.

        feedback:
        +1.0 = DJ liked the AI decision
         0.0 = neutral
        -1.0 = DJ disliked the AI decision
        """

        observation = {
            "timestamp": datetime.now().isoformat(),
            "song_time": float(time),
            "music_event": music_event,
            "ai_action": ai_action,
            "dj_action": dj_action,
            "feedback": float(feedback)
        }

        self.observations.append(observation)

    def get_observations(self):
        return self.observations

    def save(self, file_path):

        folder = os.path.dirname(file_path)

        if folder:
            os.makedirs(folder, exist_ok=True)

        data = {
            "dj_name": self.dj_name,
            "observations": self.observations
        }

        with open(
            file_path,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                data,
                file,
                indent=4
            )

    def load(self, file_path):

        if not os.path.exists(file_path):
            return

        with open(
            file_path,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        self.dj_name = data.get(
            "dj_name",
            self.dj_name
        )

        self.observations = data.get(
            "observations",
            []
        )

    def show_observations(self):

        print("\n==============================")
        print("       DJ OBSERVATIONS")
        print("==============================")

        print(
            f"DJ: {self.dj_name}"
        )

        print(
            f"Observations: "
            f"{len(self.observations)}"
        )

        for observation in self.observations:

            print(
                f"{observation['song_time']:.2f}s | "
                f"{observation['music_event']} | "
                f"AI: {observation['ai_action']} | "
                f"DJ: {observation['dj_action']} | "
                f"Feedback: {observation['feedback']}"
            )